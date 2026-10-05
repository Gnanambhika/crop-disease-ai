import {Api} from './api.js';
import {node, button, table} from './dom.js';

const api = new Api();
const content = document.querySelector('#content');
const message = document.querySelector('#message');
const dialog = document.querySelector('#editor');
const form = document.querySelector('#editor-form');
let currentView = 'dashboard';
let generation = 0;
let user;
let saveEditor;
let mutating = false;
const pageSize = 50;
let offset = 0;
let feedbackStatus = '';
const date = value => new Date(value).toLocaleString();

function signOut() {
  api.token = null; user = null; generation++;
  dialog.close(); content.replaceChildren();
  document.querySelector('#workspace').hidden = true;
  document.querySelector('#login-panel').hidden = false;
  document.querySelector('#logout').hidden = true;
  document.querySelector('#identity').hidden = true;
}
function report(error) {
  if (error.status === 401 || error.status === 403) signOut();
  message.textContent = error.message || 'This action could not be completed.';
}
document.querySelector('#logout').addEventListener('click', () => { signOut(); message.textContent = 'Signed out.'; });
document.querySelector('#login-form').addEventListener('submit', async event => {
  event.preventDefault(); const target = event.currentTarget; const submit = target.querySelector('button');
  submit.disabled = true; message.textContent = 'Signing in…';
  const values = new FormData(target);
  try {
    user = await api.login(values.get('email').trim(), values.get('password'));
    target.reset(); document.querySelector('#login-panel').hidden = true;
    document.querySelector('#workspace').hidden = false; document.querySelector('#logout').hidden = false;
    document.querySelector('#identity').textContent = user.display_name;
    document.querySelector('#identity').hidden = false;
    await navigate('dashboard');
  } catch (error) { report(error); }
  finally { submit.disabled = false; }
});
document.querySelectorAll('[data-view]').forEach(item => item.addEventListener('click', () => navigate(item.dataset.view)));

async function navigate(view, preserveOffset = false) {
  if (!preserveOffset) offset = 0;
  currentView = view; const revision = ++generation;
  document.querySelectorAll('[data-view]').forEach(item => {
    if (item.dataset.view === view) item.setAttribute('aria-current', 'page'); else item.removeAttribute('aria-current');
  });
  message.textContent = 'Loading…'; content.replaceChildren();
  try {
    const page = await render(view);
    if (revision !== generation || !api.token) return;
    content.replaceChildren(page); message.textContent = '';
  } catch (error) { if (revision === generation) report(error); }
}
async function mutate(action, success) {
  if (mutating) return;
  mutating = true;
  message.textContent = 'Saving changes…';
  const controls = [...document.querySelectorAll('#content button')];
  controls.forEach(item => item.disabled = true);
  try { await action(); await navigate(currentView, true); message.textContent = success; }
  catch (error) { report(error); }
  finally { mutating = false; controls.forEach(item => item.disabled = false); }
}
function toolbar(page, title, extra = []) {
  const descriptions = {dashboard:'A clear view of your research workspace.', crops:'Manage the crop catalog connected to your disease categories.', diseases:'Review model categories and maintain crop information.', treatments:'Maintain care drafts and their source references.', users:'Manage access to optional cloud backup.', predictions:'Actual model outputs backed up from farmer devices.', feedback:'Review farmer messages and resolve open feedback.'};
  const bar = node('div', undefined, 'toolbar');
  const heading = node('div'); heading.append(node('div','Administration','eyebrow'),node('h1', title),node('p',descriptions[currentView],'muted')); bar.append(heading);
  const actions = node('div', undefined, 'actions'); actions.append(...extra, button('Refresh', () => navigate(currentView, true)));
  bar.append(actions); page.append(bar);
}
function pager(page, count) {
  const actions = node('div', undefined, 'actions');
  const previous = button('Previous', () => { offset = Math.max(0, offset - pageSize); navigate(currentView, true); }); previous.disabled = offset === 0;
  const next = button('Next', () => { offset += pageSize; navigate(currentView, true); }); next.disabled = count < pageSize;
  actions.append(previous, node('span', `Page ${offset / pageSize + 1}`), next); page.append(actions);
}
function edit(title, fields, values, save) {
  document.querySelector('#editor-title').textContent = title;
  document.querySelector('#editor-error').textContent = '';
  const container = document.querySelector('#editor-fields'); container.replaceChildren();
  for (const field of fields) {
    const label = node('label', field.title);
    const input = node(field.options ? 'select' : field.long ? 'textarea' : 'input');
    input.name = field.key; input.required = field.required !== false;
    if (field.options) field.options.forEach(option => { const item = node('option', option.name); item.value = option.id; input.append(item); });
    else { input.minLength = field.min ?? 5; if (field.max) input.maxLength = field.max; }
    input.value = values[field.key] ?? (field.options?.[0]?.id ?? '');
    label.append(input); container.append(label);
  }
  saveEditor = async () => {
    const data = Object.fromEntries(new FormData(form));
    for (const field of fields) {
      if (field.options) data[field.key] = Number(data[field.key]);
      else data[field.key] = data[field.key].trim();
    }
    if ('model_class_id' in data && !data.model_class_id) data.model_class_id = null;
    await save(data);
  };
  dialog.showModal();
}
document.querySelector('#cancel').addEventListener('click', () => dialog.close());
form.addEventListener('submit', async event => {
  event.preventDefault(); const submit = form.querySelector('[type=submit]'); submit.disabled = true;
  try { await saveEditor(); dialog.close(); await navigate(currentView); message.textContent = 'Saved.'; }
  catch (error) { if ([401,403].includes(error.status)) report(error); else document.querySelector('#editor-error').textContent = error.message; }
  finally { submit.disabled = false; }
});
function recordActions(kind, record, fields) {
  const actions = node('div', undefined, 'actions');
  actions.append(button('Edit', () => edit(`Edit ${kind}`, fields, record, data => api.request(`/${kind}/${record.id}`, 'PUT', data))),
    button('Delete', () => {
      if (confirm(`Delete this ${kind.slice(0,-1)}? Linked records may prevent deletion.`)) mutate(() => api.request(`/${kind}/${record.id}`, 'DELETE'), 'Deleted.');
    }, 'danger'));
  return actions;
}
const predictionColumns = [
  {title:'ID',value:r=>r.id}, {title:'User',value:r=>r.user_id}, {title:'Crop',value:r=>r.crop},
  {title:'Model output',value:r=>r.model_class_id}, {title:'Confidence',value:r=>`${(r.confidence*100).toFixed(1)}%${r.is_below_threshold?' · uncertain':''}`},
  {title:'Model version',value:r=>r.model_version}, {title:'Captured',value:r=>date(r.captured_at)},
];
async function render(view) {
  const page = node('div');
  if (view === 'dashboard') {
    const stats = await api.request('/admin/statistics'); toolbar(page,'Dashboard');
    const metrics = node('div',undefined,'metrics');
    for (const [title,key] of [['Users','total_users'],['Predictions','total_predictions'],['Diseases','total_diseases'],['Crops','total_crops']]) {
      const card = node('div',undefined,'card metric'); card.append(node('span',title,'metric-label'),node('strong',stats[key]),node('span',key==='total_predictions'?'Optional device backups':key==='total_diseases'?'Catalog categories':key==='total_crops'?'Catalog crops':'Registered accounts','muted small')); metrics.append(card);
    }
    page.append(metrics);
    const trend = node('section',undefined,'card trend-card');
    trend.append(node('h2','Backup activity'),node('p','Last 7 days · grouped by the date each record reached the server.','muted'));
    const maximum = Math.max(1,...stats.prediction_trend.map(r=>r.count));
    for (const row of stats.prediction_trend) {
      const item=node('div',undefined,'trend-row'); const meter=node('meter');
      meter.min=0; meter.max=maximum; meter.value=row.count;
      meter.setAttribute('aria-label',`${row.date}: ${row.count} records received`);
      item.append(node('span',row.date),meter,node('strong',row.count));trend.append(item);
    }
    trend.append(node('p','Backup counts do not measure disease prevalence or model accuracy.','small muted'));
    page.append(trend,node('h2','Recent predictions'),table(predictionColumns,stats.recent_predictions));
  } else if (['crops','diseases','treatments'].includes(view)) {
    let fields; let rows; let columns;
    if (view === 'crops') {
      rows = await api.request('/crops'); fields = [{key:'name',title:'Crop name',min:2,max:100}];
      columns = [{title:'ID',value:r=>r.id},{title:'Crop',value:r=>r.name}];
    } else if (view === 'diseases') {
      const [crops,diseases] = await Promise.all([api.request('/crops'),api.request('/diseases')]); rows = diseases;
      fields = [{key:'crop_id',title:'Crop',options:crops},{key:'name',title:'Disease name',min:2,max:150},
        {key:'model_class_id',title:'Model class ID (optional)',required:false,min:0,max:200},
        {key:'description',title:'Description',long:true},{key:'symptoms',title:'Symptoms',long:true}];
      columns = [{title:'ID',value:r=>r.id},{title:'Crop',value:r=>crops.find(c=>c.id===r.crop_id)?.name ?? r.crop_id},
        {title:'Disease',value:r=>r.name},{title:'Class ID',value:r=>r.model_class_id},
        {title:'Description / symptoms',value:r=>node('div',`${r.description}\n\n${r.symptoms}`,'wrap')}];
    } else {
      const [diseases,treatments] = await Promise.all([api.request('/diseases'),api.request('/admin/treatments')]); rows = treatments;
      fields = [{key:'disease_id',title:'Disease',options:diseases},
        ...[['prevention','Prevention'],['care_guidance','Care guidance'],['safety_precautions','Safety precautions'],['source_reference','Source / reference']].map(([key,title])=>({key,title,long:true}))];
      columns = [{title:'ID',value:r=>r.id},{title:'Disease',value:r=>diseases.find(d=>d.id===r.disease_id)?.name ?? r.disease_id},
        {title:'Review state',value:r=>r.review_status}, {title:'Guidance / sources',value:r=>node('div',`Prevention: ${r.prevention}\nCare: ${r.care_guidance}\nSafety: ${r.safety_precautions}\nSource: ${r.source_reference}`,'wrap')}];
      page.append(node('p','Treatment entries are drafts. Saving edits resets review status to DRAFT. Independent expert review and offline publication are still required; this dashboard does not publish advice to farmers.','notice'));
    }
    const add = button(`Add ${view.slice(0,-1)}`,()=>edit(`Add ${view.slice(0,-1)}`,fields,{},data=>api.request(`/${view}`,'POST',data)));
    if (fields.some(f=>f.options && !f.options.length)) add.disabled = true;
    toolbar(page,view[0].toUpperCase()+view.slice(1),[add]);
    page.append(table([...columns,{title:'Actions',value:r=>recordActions(view,r,fields)}],rows));
  } else if (view === 'users') {
    const rows = await api.request(`/admin/users?limit=${pageSize}&offset=${offset}`); toolbar(page,'Users');
    page.append(table([{title:'ID',value:r=>r.id},{title:'Name',value:r=>r.display_name},{title:'Email',value:r=>r.email},
      {title:'Role',value:r=>r.role},{title:'Status',value:r=>r.is_active?'Active':'Inactive'},
      {title:'Action',value:r=>{ const control = button(r.is_active?'Deactivate':'Activate',()=> {
        if (confirm(`${r.is_active?'Deactivate':'Activate'} ${r.email}?`)) mutate(()=>api.request(`/admin/users/${r.id}/active`,'PUT',{is_active:!r.is_active}),'Account updated.');
      }); control.disabled=r.id===user.id; return control; }}],rows)); pager(page,rows.length);
  } else if (view === 'predictions') {
    const rows = await api.request(`/admin/predictions?limit=${pageSize}&offset=${offset}`); toolbar(page,'Prediction backups');
    page.append(table(predictionColumns,rows)); pager(page,rows.length);
  } else if (view === 'feedback') {
    const rows = await api.request(`/feedback?limit=${pageSize}&offset=${offset}${feedbackStatus?`&status=${feedbackStatus}`:''}`);
    const label=node('label','Filter'); const filter=node('select');
    for(const [value,text] of [['','All'],['OPEN','Open'],['RESOLVED','Resolved']]) {const option=node('option',text);option.value=value;filter.append(option);}
    filter.value=feedbackStatus;filter.addEventListener('change',()=>{feedbackStatus=filter.value;navigate('feedback');});label.append(filter);
    toolbar(page,'Feedback',[label]);
    page.append(table([{title:'ID',value:r=>r.id},{title:'User',value:r=>r.user_id},{title:'Prediction',value:r=>r.prediction_id},
      {title:'Message',value:r=>node('div',r.message,'wrap')},{title:'Status',value:r=>r.status},{title:'Received',value:r=>date(r.created_at)},
      {title:'Action',value:r=>r.status==='OPEN'?button('Resolve',()=>mutate(()=>api.request(`/feedback/${r.id}/resolve`,'PUT'),'Feedback resolved.')):'Resolved'}],rows)); pager(page,rows.length);
  }
  return page;
}
