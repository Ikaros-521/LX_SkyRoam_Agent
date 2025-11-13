/**
 * API 配置
 */

// API 基础URL（兼容 REACT_APP_API_BASE_URL 与 REACT_APP_API_URL）
const RAW_API_BASE =
  process.env.REACT_APP_API_BASE_URL ||
  process.env.REACT_APP_API_URL ||
  'http://localhost:8001';

// 规范化基础路径，确保包含 /api/v1
const normalizedBase = RAW_API_BASE.endsWith('/api/v1')
  ? RAW_API_BASE
  : `${RAW_API_BASE.replace(/\/$/, '')}/api/v1`;

export const API_BASE_URL = normalizedBase;

// 调试信息
console.log('API_BASE_URL:', API_BASE_URL);
console.log('REACT_APP_API_BASE_URL:', process.env.REACT_APP_API_BASE_URL);
console.log('REACT_APP_API_URL:', process.env.REACT_APP_API_URL);

// API 端点
export const API_ENDPOINTS = {
  // 旅行计划
  TRAVEL_PLANS: '/travel-plans/',
  TRAVEL_PLAN_DETAIL: (id: number) => `/travel-plans/${id}`,
  TRAVEL_PLAN_GENERATE: (id: number) => `/travel-plans/${id}/generate`,
  TRAVEL_PLAN_STATUS: (id: number) => `/travel-plans/${id}/status`,
  TRAVEL_PLAN_SELECT: (id: number) => `/travel-plans/${id}/select-plan`,
  TRAVEL_PLANS_BATCH_DELETE: '/travel-plans/batch-delete',
  // 新增：公开相关
  TRAVEL_PLANS_PUBLIC: '/travel-plans/public',
  TRAVEL_PLAN_PUBLIC_DETAIL: (id: number) => `/travel-plans/public/${id}`,
  TRAVEL_PLAN_PUBLISH: (id: number) => `/travel-plans/${id}/publish`,
  TRAVEL_PLAN_UNPUBLISH: (id: number) => `/travel-plans/${id}/unpublish`,
  // 新增：评分相关
  TRAVEL_PLAN_RATINGS: (id: number) => `/travel-plans/${id}/ratings`,
  TRAVEL_PLAN_RATINGS_SUMMARY: (id: number) => `/travel-plans/${id}/ratings/summary`,
  TRAVEL_PLAN_RATINGS_ME: (id: number) => `/travel-plans/${id}/ratings/me`,
  
  // 目的地
  DESTINATIONS: '/destinations',
  DESTINATION_DETAIL: (id: number) => `/destinations/${id}`,
  
  // 用户
  USERS: '/users',
  USER_DETAIL: (id: number) => `/users/${id}`,
  USER_RESET_PASSWORD: (id: number) => `/users/${id}/reset-password`,
  
  // Agent
  AGENTS: '/agents',
  AGENT_DETAIL: (id: number) => `/agents/${id}`,
  
  // OpenAI
  OPENAI_CONFIG: '/openai/config',
  OPENAI_TEST: '/openai/test',
  
  // 地图
  MAP_STATIC: '/map/static',
  MAP_HEALTH: '/map/health',
  MAP_INPUT_TIPS: '/map/tips',
  
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
