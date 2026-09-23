import { reactive, ref } from 'vue'

/** 列表页通用逻辑：筛选条件（query）+ 服务端分页 + 加载。查询条件变更后调用 reload 从第 1 页拉取。 */
export function useTable(loader, query = {}) {
  const rows = ref([])
  const total = ref(0)
  const loading = ref(false)
  const page = reactive({ page: 1, page_size: 20 })

  async function load() {
    loading.value = true
    try {
      const data = await loader({ ...query, ...page })
      rows.value = data?.results || []
      total.value = data?.count || 0
    } catch {
      rows.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  function reload() {
    page.page = 1
    return load()
  }

  return { rows, total, loading, page, load, reload }
}
