export function saveCsv(data, filename) {
  if (!(data instanceof Blob)) data = new Blob(['\ufeff' + data], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
