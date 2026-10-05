export function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = String(text);
  if (className) element.className = className;
  return element;
}
export function button(text, action, className = 'secondary') {
  const element = node('button', text, className);
  element.type = 'button';
  element.addEventListener('click', action);
  return element;
}
export function table(columns, rows) {
  const wrapper = node('div', undefined, 'table-wrap');
  const element = node('table');
  const head = node('thead'); const header = node('tr');
  columns.forEach(column => { const th = node('th', column.title); th.scope = 'col'; header.append(th); });
  head.append(header); element.append(head);
  const body = node('tbody');
  for (const row of rows) {
    const tr = node('tr');
    for (const column of columns) {
      const td = node('td'); const value = column.value(row);
      if (value instanceof Node) td.append(value); else td.textContent = String(value ?? '—');
      tr.append(td);
    }
    body.append(tr);
  }
  if (!rows.length) { const tr = node('tr'); const td = node('td', 'No records found.'); td.colSpan = columns.length; tr.append(td); body.append(tr); }
  element.append(body); wrapper.append(element); return wrapper;
}
