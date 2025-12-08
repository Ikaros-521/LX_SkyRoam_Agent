import React, { useState, useRef, useEffect } from 'react';
import { FloatButton, Modal, Input, Button, List, Avatar, Spin, Space, Typography, message } from 'antd';
import { MessageOutlined, SendOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { getToken } from '../../utils/auth';
import './AIAssistant.css';

const { TextArea } = Input;
const { Text } = Typography;

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

// 上下文长度限制配置（默认值，会从后端 API 获取实际配置）
const DEFAULT_MAX_CONTEXT_TOKENS = 12000; // 默认最大上下文 token 数
const DEFAULT_ESTIMATED_CHARS_PER_TOKEN = 2; // 默认估算：1 token ≈ 2 字符（中文为主）
const DEFAULT_MAX_RECENT_MESSAGES = 20; // 默认最多保留最近 N 轮对话

/**
 * 估算文本的 token 数量（粗略估算）
 */
const estimateTokens = (text: string, charsPerToken: number = DEFAULT_ESTIMATED_CHARS_PER_TOKEN): number => {
  // 中文和英文混合，粗略估算
  return Math.ceil(text.length / charsPerToken);
};

/**
 * 智能截断对话历史，确保不超过 token 限制
 * 策略：
 * 1. 优先保留最近的对话（最多 maxRecentMessages 轮）
 * 2. 如果还有空间，保留初始上下文的核心部分
 * 3. 如果初始上下文太长，截断但保留开头和关键信息
 */
const truncateConversationHistory = (
  messages: Array<{ role: string; content: string }>,
  maxContextTokens: number = DEFAULT_MAX_CONTEXT_TOKENS,
  charsPerToken: number = DEFAULT_ESTIMATED_CHARS_PER_TOKEN,
  maxRecentMessages: number = DEFAULT_MAX_RECENT_MESSAGES
): Array<{ role: string; content: string }> => {
  if (messages.length === 0) return [];

  // 分离初始上下文（第一个 assistant 消息，通常是长文本）和后续对话
  const initialContext = messages[0]?.role === 'assistant' ? messages[0] : null;
  const conversationMessages = initialContext ? messages.slice(1) : messages;

  // 保留最近的对话（最多 maxRecentMessages 轮，即 maxRecentMessages * 2 条消息）
  const recentMessages = conversationMessages.slice(-maxRecentMessages * 2);

  // 计算已使用的 token 数
  let usedTokens = recentMessages.reduce((sum, msg) => sum + estimateTokens(msg.content, charsPerToken), 0);

  // 如果有初始上下文，尝试添加它（可能需要截断）
  if (initialContext) {
    const initialTokens = estimateTokens(initialContext.content, charsPerToken);
    const remainingTokens = maxContextTokens - usedTokens - 1000; // 留出 1000 tokens 缓冲

    if (initialTokens <= remainingTokens) {
      // 初始上下文可以完整保留
      return [initialContext, ...recentMessages];
    } else if (remainingTokens > 1000) {
      // 初始上下文太长，需要截断
      // 保留开头部分（通常包含重要信息）和结尾部分
      const maxInitialChars = (remainingTokens - 500) * charsPerToken; // 留出 500 tokens
      const keepStartChars = Math.floor(maxInitialChars * 0.6); // 保留 60% 的开头
      const keepEndChars = Math.floor(maxInitialChars * 0.4); // 保留 40% 的结尾

      const truncatedContent = 
        initialContext.content.substring(0, keepStartChars) +
        '\n\n[... 内容已截断以节省上下文空间 ...]\n\n' +
        initialContext.content.substring(initialContext.content.length - keepEndChars);

      return [
        { ...initialContext, content: truncatedContent },
        ...recentMessages
      ];
    } else {
      // 剩余空间太小，不添加初始上下文，只保留最近对话
      return recentMessages;
    }
  }

  return recentMessages;
};

const AIAssistant: React.FC = () => {
  const [visible, setVisible] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<any>(null);
  
  // 配置状态（从后端获取）
  const [config, setConfig] = useState<{
    maxInputTokens: number;
    estimatedCharsPerToken: number;
    maxRecentMessages: number;
  }>({
    maxInputTokens: DEFAULT_MAX_CONTEXT_TOKENS,
    estimatedCharsPerToken: DEFAULT_ESTIMATED_CHARS_PER_TOKEN,
    maxRecentMessages: DEFAULT_MAX_RECENT_MESSAGES,
  });
  
  // 从后端获取配置
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const token = getToken();
        if (!token) return;
        
        const response = await fetch(buildApiUrl(API_ENDPOINTS.OPENAI_CONFIG), {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data.config) {
            setConfig({
              maxInputTokens: data.config.max_input_tokens || DEFAULT_MAX_CONTEXT_TOKENS,
              estimatedCharsPerToken: data.config.estimated_chars_per_token || DEFAULT_ESTIMATED_CHARS_PER_TOKEN,
              maxRecentMessages: data.config.max_recent_messages || DEFAULT_MAX_RECENT_MESSAGES,
            });
          }
        }
      } catch (error) {
        console.warn('获取 AI 配置失败，使用默认值:', error);
      }
    };
    
    fetchConfig();
  }, []);

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (visible) {
      scrollToBottom();
      // 延迟聚焦输入框
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [visible, messages]);

  // 监听来自外部的事件，用于设置初始消息上下文
  useEffect(() => {
    const handleSetContext = (event: CustomEvent) => {
      const { context, openModal = true } = event.detail || {};
      if (context) {
        // 设置初始消息
        const initialMessages: Message[] = [
          {
            role: 'assistant',
            content: context,
            timestamp: Date.now()
          }
        ];
        setMessages(initialMessages);
        
        // 如果需要，自动打开对话框
        if (openModal) {
          setVisible(true);
        }
      }
    };

    window.addEventListener('ai-assistant:set-context', handleSetContext as EventListener);
    
    return () => {
      window.removeEventListener('ai-assistant:set-context', handleSetContext as EventListener);
    };
  }, []);

  // 发送消息（流式）
  const handleSend = async () => {
    if (!inputValue.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: inputValue.trim(),
      timestamp: Date.now()
    };

    // 添加用户消息
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInputValue('');
    setLoading(true);

    // 创建AI消息占位符
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: Date.now() + 1 // 确保时间戳不同
    };
    const messagesWithAssistant = [...newMessages, assistantMessage];
    setMessages(messagesWithAssistant);

    try {
      // 构建对话历史（只包含role和content）
      const conversationHistory = newMessages
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }));

      // 智能截断对话历史，确保不超过 token 限制
      const truncatedHistory = truncateConversationHistory(
        conversationHistory.slice(0, -1), // 排除当前用户消息
        config.maxInputTokens,
        config.estimatedCharsPerToken,
        config.maxRecentMessages
      );

      // 检查是否进行了截断
      const wasTruncated = truncatedHistory.length < conversationHistory.length - 1 ||
        truncatedHistory.some((msg, idx) => {
          const original = conversationHistory[idx];
          return original && msg.content !== original.content;
        });

      if (wasTruncated) {
        console.warn('对话历史已自动截断以符合上下文长度限制');
        // 可选：显示提示信息（但不打断用户体验）
        // message.info('对话历史较长，已自动截断以保持响应速度', 2);
      }

      // 获取token
      const token = getToken();
      if (!token) {
        throw new Error('未登录');
      }

      // 调用流式API
      const response = await fetch(buildApiUrl(API_ENDPOINTS.OPENAI_CHAT_STREAM), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_history: truncatedHistory,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: '请求失败' }));
        throw new Error(errorData.detail || `请求失败 (${response.status})`);
      }

      // 读取流式响应
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';

      if (!reader) {
        throw new Error('无法读取响应流');
      }

      const updateMessage = (content: string) => {
        setMessages(prev => {
          const updated = [...prev];
          // 查找最后一个AI消息（role为assistant且可能是空的）
          // 从后往前查找，找到第一个assistant消息
          let targetIndex = -1;
          for (let i = updated.length - 1; i >= 0; i--) {
            if (updated[i].role === 'assistant') {
              targetIndex = i;
              break;
            }
          }
          
          // 如果找到了，更新它
          if (targetIndex !== -1) {
            updated[targetIndex] = {
              ...updated[targetIndex],
              content: content
            };
          }
          return updated;
        });
        // 滚动到底部
        setTimeout(() => scrollToBottom(), 10);
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'content') {
                accumulatedContent += data.content;
                updateMessage(accumulatedContent);
              } else if (data.type === 'done') {
                setLoading(false);
                updateMessage(accumulatedContent);
              } else if (data.type === 'error') {
                throw new Error(data.message || '流式响应错误');
              }
            } catch (e) {
              // 忽略JSON解析错误
              console.warn('解析流式数据失败:', e);
            }
          }
        }
      }
    } catch (error: any) {
      console.error('AI对话失败:', error);
      message.error(error.message || 'AI对话失败，请稍后重试');
      setLoading(false);
      
      // 更新错误消息
      setMessages(prev => {
        const updated = [...prev];
        // 查找最后一个AI消息（role为assistant）
        let targetIndex = -1;
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].role === 'assistant') {
            targetIndex = i;
            break;
          }
        }
        if (targetIndex !== -1) {
          updated[targetIndex] = {
            ...updated[targetIndex],
            content: `抱歉，我遇到了一些问题：${error.message || '未知错误'}`
          };
        }
        return updated;
      });
    }
  };

  // 清空对话
  const handleClear = () => {
    setMessages([]);
    message.success('对话已清空');
  };

  // 处理键盘事件
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      <FloatButton
        icon={<MessageOutlined />}
        type="primary"
        style={{
          right: 24,
          bottom: 24,
          width: 56,
          height: 56,
        }}
        onClick={() => setVisible(true)}
      />

      <Modal
        title={
          <Space>
            <RobotOutlined style={{ color: '#6366f1' }} />
            <span>AI 助手</span>
          </Space>
        }
        open={visible}
        onCancel={() => setVisible(false)}
        footer={null}
        width={800}
        className="ai-assistant-modal"
        styles={{
          body: {
            padding: 0,
            height: '600px',
            display: 'flex',
            flexDirection: 'column',
          }
        }}
      >
        <div className="ai-assistant-container">
          {/* 消息列表 */}
          <div className="ai-assistant-messages">
            {messages.length === 0 ? (
              <div className="ai-assistant-empty">
                <RobotOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
                <Text type="secondary">我是您的AI旅行助手，有什么问题可以问我哦~</Text>
                <div style={{ marginTop: 24 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    提示：您可以复制页面上的内容到这里提问
                  </Text>
                </div>
              </div>
            ) : (
              <List
                dataSource={messages}
                renderItem={(item) => (
                  <List.Item
                    style={{
                      border: 'none',
                      padding: '12px 16px',
                      justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start',
                    }}
                  >
                    <div
                      className={`ai-message ${item.role === 'user' ? 'ai-message-user' : 'ai-message-assistant'}`}
                    >
                      <Space align="start" size={12}>
                        {item.role === 'assistant' && (
                          <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#6366f1', flexShrink: 0 }} />
                        )}
                        <div className="ai-message-content">
                          <div className="ai-message-text">{item.content}</div>
                        </div>
                        {item.role === 'user' && (
                          <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#10b981', flexShrink: 0 }} />
                        )}
                      </Space>
                    </div>
                  </List.Item>
                )}
              />
            )}
            {loading && (
              <div style={{ padding: '12px 16px', display: 'flex', justifyContent: 'flex-start' }}>
                <Space>
                  <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#6366f1' }} />
                  <Spin size="small" />
                  <Text type="secondary">AI正在思考...</Text>
                </Space>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div className="ai-assistant-input">
            <Space.Compact style={{ width: '100%' }}>
              <TextArea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入您的问题...（Shift+Enter换行，Enter发送）"
                autoSize={{ minRows: 1, maxRows: 4 }}
                disabled={loading}
                style={{ resize: 'none' }}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSend}
                loading={loading}
                disabled={!inputValue.trim()}
                style={{ height: 'auto' }}
              >
                发送
              </Button>
            </Space.Compact>
            {messages.length > 0 && (
              <Button
                type="text"
                size="small"
                onClick={handleClear}
                style={{ marginTop: 8, padding: 0 }}
              >
                清空对话
              </Button>
            )}
          </div>
        </div>
      </Modal>
    </>
  );
};

export default AIAssistant;

