/**
 * uni.request 封装
 * - 统一 baseURL（可配：src/utils/config.js）
 * - 自动携带 Bearer token
 * - code 40100 时用 refresh 静默续签；续签失败跳登录
 * - 统一解析 {code,message,data}，失败 uni.showToast
 */
import store from '../store'
import { BASE_URL } from './config'

let refreshing = null

function toast(message) {
  uni.showToast({ title: message || '请求失败', icon: 'none', duration: 2000 })
}

function raw({ url, method = 'GET', data, header = {} }) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      method,
      data,
      header: { 'Content-Type': 'application/json', ...header },
      timeout: 20000,
      success: (res) => resolve(res),
      fail: (err) => reject(err),
    })
  })
}

// 静默续签：并发请求共用同一个 refresh Promise
function refreshToken() {
  if (!refreshing) {
    refreshing = raw({ url: '/auth/refresh', method: 'POST', data: { refresh: store.state.refresh } })
      .then((res) => {
        const body = res.data || {}
        if (res.statusCode === 200 && body.code === 0 && body.data?.access) {
          store.saveAuth({ access: body.data.access, refresh: body.data.refresh })
          return store.state.access
        }
        throw new Error('refresh failed')
      })
      .catch((e) => {
        store.toLogin()
        throw e
      })
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

/**
 * @param {string} url  以 / 开头的相对路径
 * @param {object} opts { method, data, header, silent(不弹 toast), retry(内部用) }
 * @returns {Promise<any>} 解析后的 data
 */
export async function request(url, opts = {}) {
  const { method = 'GET', data, header = {}, silent = false, retry = false } = opts
  const token = store.getToken()
  const res = await raw({
    url,
    method,
    data,
    header: token ? { Authorization: `Bearer ${token}`, ...header } : header,
  }).catch((err) => {
    if (!silent) toast('网络异常，请稍后重试')
    throw err
  })

  const body = res.data || {}
  if (res.statusCode === 401 || body.code === 40100) {
    try {
      await refreshToken()
    } catch (e) {
      const err = new Error('登录已失效')
      err.code = 40100
      throw err
    }
    // 幂等请求自动重放一次，写操作由调用方重试，避免重复下单
    if (!retry && ['GET', 'HEAD'].includes(method.toUpperCase())) {
      return request(url, { ...opts, retry: true })
    }
    if (!silent) toast('登录已刷新，请重试')
    const err = new Error('登录已刷新，请重试')
    err.code = 40100
    throw err
  }

  if (body.code !== 0) {
    const msg = body.message || `请求失败(${body.code})`
    if (!silent) toast(msg)
    const err = new Error(msg)
    err.code = body.code
    err.data = body.data
    throw err
  }
  return body.data
}

export const get = (url, data, opts) => request(url, { method: 'GET', data, ...opts })
export const post = (url, data, opts) => request(url, { method: 'POST', data, ...opts })

/**
 * 上传文件（multipart），kind: evidence / student_card / appeal
 * @returns {Promise<{id:number,name:string}>}
 */
export function upload(filePath, kind = 'evidence') {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${BASE_URL}/files`,
      filePath,
      name: 'file',
      formData: { kind },
      header: { Authorization: `Bearer ${store.getToken()}` },
      success: (res) => {
        let body = {}
        try {
          body = JSON.parse(res.data)
        } catch (e) {
          toast('上传响应解析失败')
          return reject(e)
        }
        if (body.code === 40100) {
          store.toLogin()
          return reject(new Error('登录已失效'))
        }
        if (body.code !== 0) {
          toast(body.message || '上传失败')
          const err = new Error(body.message || '上传失败')
          err.code = body.code
          return reject(err)
        }
        resolve(body.data)
      },
      fail: (err) => {
        toast('上传失败')
        reject(err)
      },
    })
  })
}

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
function toBase64(buffer) {
  const bytes = new Uint8Array(buffer)
  let out = ''
  for (let i = 0; i < bytes.length; i += 3) {
    const [a, b, c] = [bytes[i], bytes[i + 1], bytes[i + 2]]
    out += B64[a >> 2] + B64[((a & 3) << 4) | (b >> 4)]
    out += b === undefined ? '==' : B64[((b & 15) << 2) | (c >> 6)] + (c === undefined ? '=' : B64[c & 63])
  }
  return out
}

/** 带鉴权下载文件 → 可直接给 <image> 用的临时地址（裸 MEDIA 不开放） */
export function fileUrl(id) {
  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url: `${BASE_URL}/files/${id}`,
      header: { Authorization: `Bearer ${store.getToken()}` },
      success: (res) => (res.statusCode === 200 ? resolve(res.tempFilePath) : reject(new Error('下载失败'))),
      fail: reject,
    })
  })
}

/** 查看凭证：下载后调起系统预览 */
export async function viewFile(id) {
  try {
    const path = await fileUrl(id)
    uni.previewImage({ urls: [path] })
  } catch (e) {
    toast('凭证加载失败')
  }
}

/** #ifdef H5 内联展示用 dataURL（<image> 无法带 Authorization 头） */
export function fileDataUrl(id) {
  return raw({ url: `/files/${id}`, method: 'GET', header: { Accept: 'image/*' } }).then((res) => {
    if (res.statusCode !== 200) throw new Error('加载失败')
    return `data:image/*;base64,${toBase64(res.data)}`
  })
}

export default { request, get, post, upload, fileUrl, viewFile, fileDataUrl }
