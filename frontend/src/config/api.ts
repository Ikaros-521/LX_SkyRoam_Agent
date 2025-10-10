/**
 * API 配置
 */

// API 基础URL
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8001/api/v1';

// 调试信息
console.log('API_BASE_URL:', API_BASE_URL);
console.log('REACT_APP_API_BASE_URL:', process.env.REACT_APP_API_BASE_URL);

// API 端点
export const API_ENDPOINTS = {
  // 旅行计划
  TRAVEL_PLANS: '/travel-plans/',
  TRAVEL_PLAN_DETAIL: (id: number) => `/travel-plans/${id}`,
  TRAVEL_PLAN_GENERATE: (id: number) => `/travel-plans/${id}/generate`,
  TRAVEL_PLAN_STATUS: (id: number) => `/travel-plans/${id}/status`,
  
  // 目的地
  DESTINATIONS: '/destinations',
  DESTINATION_DETAIL: (id: number) => `/destinations/${id}`,
  
  // 用户
  USERS: '/users',
  USER_DETAIL: (id: number) => `/users/${id}`,
  
  // Agent
  AGENTS: '/agents',
  AGENT_DETAIL: (id: number) => `/agents/${id}`,
  
  // OpenAI
  OPENAI_CONFIG: '/openai/config',
  OPENAI_TEST: '/openai/test',
  
  // 健康检查
  HEALTH: '/health'
};

// 请求配置
export const REQUEST_CONFIG = {
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
};

// 构建完整的API URL
export const buildApiUrl = (endpoint: string): string => {
  return `${API_BASE_URL}${endpoint}`;
};
