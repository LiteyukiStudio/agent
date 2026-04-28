/**
 * 应用级常量：名称、描述、版本等。
 * 所有页面标题、品牌文案统一从此处引用，便于集中修改和 i18n 迁移。
 */

export const APP = {
  name: 'LiteYuki SRE',
  fullName: 'LiteYuki SRE Agent',
  description: '多智能体 SRE 运维助手',
  version: '0.1.0',
  copyright: '© 2026 LiteyukiStudio',
} as const

export const PAGE_TITLES = {
  login: '登录',
  chat: '聊天',
  settings: '设置',
  admin: '管理面板',
  adminUsers: '用户管理',
  adminOAuth: 'OAuth 配置',
  adminQuota: '配额方案',
} as const

export const NAV_LABELS = {
  newChat: '新建对话',
  settings: '设置',
  admin: '管理',
  logout: '退出登录',
  darkMode: '深色模式',
  lightMode: '浅色模式',
} as const

export const AUTH_LABELS = {
  username: '用户名',
  password: '密码',
  login: '登录',
  loginWith: '使用 {provider} 登录',
  loginFailed: '登录失败，请检查用户名和密码',
  noProviders: '暂无可用的第三方登录方式',
} as const

export const CHAT_LABELS = {
  placeholder: '输入消息，Enter 发送，Shift+Enter 换行',
  send: '发送',
  noMessages: '开始新对话吧',
  toolCall: '工具调用',
  thinking: '思考中...',
} as const

export const SETTINGS_LABELS = {
  apiTokens: 'API 令牌',
  createToken: '创建令牌',
  tokenName: '令牌名称',
  tokenScopes: '权限范围',
  tokenCreated: '令牌已创建，请立即保存（仅显示一次）',
  revoke: '吊销',
  usage: '用量统计',
  daily: '今日',
  weekly: '本周',
  monthly: '本月',
  used: '已用',
  remaining: '剩余',
  unlimited: '无限制',
} as const

export const ADMIN_LABELS = {
  users: '用户',
  oauthProviders: 'OAuth 提供商',
  quotaPlans: '配额方案',
  role: '角色',
  actions: '操作',
  save: '保存',
  cancel: '取消',
  delete: '删除',
  create: '创建',
  edit: '编辑',
  confirm: '确认',
  noData: '暂无数据',
} as const
