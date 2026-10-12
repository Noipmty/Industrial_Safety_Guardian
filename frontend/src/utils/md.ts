/**
 * 极简 Markdown 渲染（仅用于 mock 回答文本）：
 * 支持 **加粗**、换行、[n] 引用徽标。输出前先做 HTML 转义，避免注入。
 */
export function renderLiteMarkdown(src: string): string {
  const esc = src
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  return esc
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[(\d)\]/g, '<span class="ref-badge">$1</span>')
    .replace(/\n/g, '<br>')
}
