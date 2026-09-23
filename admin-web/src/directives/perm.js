/** v-perm：仅 super_admin 可见（规则配置 / 封禁用户等），operator 直接不渲染 */
export default {
  mounted(el, binding) {
    let user = null
    try {
      user = JSON.parse(localStorage.getItem('admin_user'))
    } catch {
      user = null
    }
    const allow = binding.value === undefined ? 'super_admin' : binding.value
    if (user?.role !== allow) el.parentNode?.removeChild(el)
  },
}
