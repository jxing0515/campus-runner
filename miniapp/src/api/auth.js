import { get, post, upload } from '../utils/request'

export const register = (data) => post('/auth/register', data)
export const login = (data) => post('/auth/login', data)
export const refresh = (data) => post('/auth/refresh', data)
export const logout = (data) => post('/auth/logout', data)
export const me = () => get('/auth/me')
export const changePassword = (data) => post('/auth/password', data)
export const uploadFile = (filePath, kind) => upload(filePath, kind)

// 微信授权登录：仅占位，不实装（后端未提供该接口）
export const wxLogin = () => Promise.reject(new Error('微信授权登录暂未开放，请使用学号密码登录'))

export default { register, login, refresh, logout, me, changePassword, uploadFile, wxLogin }
