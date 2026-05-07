// FitForge — App Logic
let currentSession = null, timerInterval = null, timerSeconds = 0, restInterval = null;

// ── Navigation ──
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    link.classList.add('active');
    document.getElementById('tab-' + link.dataset.tab).classList.add('active');
    if (link.dataset.tab === 'dashboard') loadDashboard();
    if (link.dataset.tab === 'exercises') loadExercises();
    if (link.dataset.tab === 'templates') loadTemplates();
    if (link.dataset.tab === 'history') loadHistory();
  });
});

// ── API helpers ──
const api = (url, opts) => fetch(url, { headers: { 'Content-Type': 'application/json' }, ...opts }).then(r => r.json());

// ── Dashboard ──
async function loadDashboard() {
  const stats = await api('/api/stats');
  document.getElementById('stats-grid').innerHTML = [
    { icon: '🏋️', val: stats.total_workouts, label: 'Total Workouts' },
    { icon: '🔥', val: stats.current_streak, label: 'Day Streak' },
    { icon: '📅', val: stats.weekly_workouts, label: 'This Week' },
    { icon: '💪', val: stats.total_sets, label: 'Total Sets' },
    { icon: '⚡', val: formatVolume(stats.total_volume), label: 'Total Volume' },
  ].map(s => `<div class="stat-card"><div class="stat-icon">${s.icon}</div><div class="stat-value">${s.val}</div><div class="stat-label">${s.label}</div></div>`).join('');

  const prEl = document.getElementById('pr-list');
  if (stats.personal_records.length === 0) {
    prEl.innerHTML = '<p style="color:var(--text2);font-size:.85rem">No records yet. Start a workout!</p>';
  } else {
    prEl.innerHTML = stats.personal_records.map(p =>
      `<div class="pr-item"><span>${p.exercise_name}</span><span class="pr-weight">${p.max_weight} kg × ${p.max_reps}</span></div>`
    ).join('');
  }

  const catEl = document.getElementById('cat-chart');
  if (stats.category_breakdown.length === 0) {
    catEl.innerHTML = '<p style="color:var(--text2);font-size:.85rem">Train to see your breakdown</p>';
  } else {
    const maxVol = Math.max(...stats.category_breakdown.map(c => c.volume || 1));
    catEl.innerHTML = stats.category_breakdown.map(c => {
      const pct = Math.round(((c.volume || 0) / maxVol) * 100);
      return `<div class="cat-bar-row"><span class="cat-label">${c.category}</span><div class="cat-bar-bg"><div class="cat-bar" style="width:${pct}%"></div></div><span class="cat-val">${c.sets_count} sets</span></div>`;
    }).join('');
  }
}

function formatVolume(v) {
  if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M';
  if (v >= 1000) return (v / 1000).toFixed(1) + 'K';
  return v;
}

// ── Exercises ──
async function loadExercises() {
  const cat = document.getElementById('cat-filter').value;
  const url = cat ? `/api/exercises?category=${cat}` : '/api/exercises';
  const exercises = await api(url);
  document.getElementById('exercise-list').innerHTML = exercises.map(e =>
    `<div class="exercise-card">
      <span class="badge badge-${e.category.toLowerCase()}">${e.category}</span>
      <h3>${e.name}</h3>
      <div class="meta"><span>🎯 ${e.muscle_group}</span><span>🔧 ${e.equipment}</span></div>
      ${e.description ? `<div class="desc">${e.description}</div>` : ''}
    </div>`
  ).join('');
}
document.getElementById('cat-filter').addEventListener('change', loadExercises);

function showAddExercise() { document.getElementById('add-exercise-modal').classList.remove('hidden'); }
function closeModal() { document.querySelectorAll('.modal').forEach(m => m.classList.add('hidden')); }

async function addExercise() {
  await api('/api/exercises', {
    method: 'POST', body: JSON.stringify({
      name: document.getElementById('ex-name').value,
      category: document.getElementById('ex-cat').value,
      muscle_group: document.getElementById('ex-muscle').value,
      equipment: document.getElementById('ex-equip').value,
      description: document.getElementById('ex-desc').value,
    })
  });
  closeModal();
  loadExercises();
}

// ── Templates ──
async function loadTemplates() {
  const templates = await api('/api/templates');
  document.getElementById('template-list').innerHTML = templates.map(t =>
    `<div class="template-card">
      <h3>${t.name}</h3>
      <div class="t-desc">${t.description || ''}</div>
      <div class="t-exercises">${t.exercises.slice(0, 5).map(e => `<span>• ${e.exercise_name} — ${e.sets}×${e.reps}</span>`).join('')}
        ${t.exercises.length > 5 ? `<span style="color:var(--accent2)">+${t.exercises.length - 5} more</span>` : ''}
      </div>
      <div class="template-actions">
        <button class="btn btn-primary btn-sm" onclick="startWorkout(${t.id},'${t.name.replace(/'/g, "\\'")}')">▶ Start</button>
        <button class="btn btn-ghost btn-sm btn-danger" onclick="deleteTemplate(${t.id})">🗑️</button>
      </div>
    </div>`
  ).join('');
}

async function deleteTemplate(id) {
  if (confirm('Delete this template?')) {
    await api(`/api/templates/${id}`, { method: 'DELETE' });
    loadTemplates();
  }
}

// ── Active Workout ──
async function startWorkout(templateId, name) {
  const res = await api('/api/sessions', { method: 'POST', body: JSON.stringify({ template_id: templateId, name }) });
  currentSession = res.session_id;
  timerSeconds = 0;
  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    timerSeconds++;
    document.getElementById('timer').textContent = formatTime(timerSeconds);
  }, 1000);

  // Switch to active tab
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelector('[data-tab="active"]').classList.add('active');
  document.getElementById('tab-active').classList.add('active');

  document.getElementById('no-active').classList.add('hidden');
  document.getElementById('active-workout').classList.remove('hidden');
  document.getElementById('active-name').textContent = name;
  loadActiveSession();
}

async function loadActiveSession() {
  const data = await api(`/api/sessions/${currentSession}`);
  // Group sets by exercise
  const grouped = {};
  data.sets.forEach(s => {
    if (!grouped[s.exercise_id]) grouped[s.exercise_id] = { name: s.exercise_name, category: s.category, sets: [] };
    grouped[s.exercise_id].sets.push(s);
  });

  document.getElementById('active-exercises').innerHTML = Object.entries(grouped).map(([eid, ex]) =>
    `<div class="active-ex-card">
      <h3><span class="badge badge-${ex.category.toLowerCase()}">${ex.category}</span> ${ex.name}</h3>
      ${ex.sets.map(s =>
      `<div class="set-row" id="set-${s.id}">
          <span class="set-num">Set ${s.set_number}</span>
          <div><input class="set-input" type="number" value="${s.weight || ''}" placeholder="kg" id="w-${s.id}"><div class="set-label">Weight</div></div>
          <div><input class="set-input" type="number" value="${s.reps || ''}" placeholder="reps" id="r-${s.id}"><div class="set-label">Reps</div></div>
          <button class="set-done ${s.completed ? 'completed' : ''}" onclick="completeSet(${s.id},${eid})" id="btn-${s.id}">${s.completed ? '✓' : '○'}</button>
        </div>`
    ).join('')}
      <button class="btn btn-ghost btn-sm" style="margin-top:.6rem" onclick="addSetToExercise(${eid})">+ Add Set</button>
    </div>`
  ).join('');
}

async function completeSet(setId, exerciseId) {
  const w = parseFloat(document.getElementById('w-' + setId).value) || 0;
  const r = parseInt(document.getElementById('r-' + setId).value) || 0;
  const res = await api(`/api/sessions/${currentSession}/sets/${setId}`, {
    method: 'PUT', body: JSON.stringify({ weight: w, reps: r })
  });
  const btn = document.getElementById('btn-' + setId);
  btn.classList.add('completed');
  btn.textContent = '✓';
  if (res.new_pr) { btn.classList.add('pr-pop'); setTimeout(() => btn.classList.remove('pr-pop'), 500); alert('🎉 New Personal Record!'); }
  startRest(60);
}

async function addSetToExercise(exerciseId) {
  await api(`/api/sessions/${currentSession}/sets`, { method: 'POST', body: JSON.stringify({ exercise_id: exerciseId }) });
  loadActiveSession();
}

function startRest(seconds) {
  const overlay = document.getElementById('rest-overlay');
  const display = document.getElementById('rest-timer');
  overlay.classList.remove('hidden');
  let remaining = seconds;
  display.textContent = remaining;
  clearInterval(restInterval);
  restInterval = setInterval(() => {
    remaining--;
    display.textContent = remaining;
    if (remaining <= 0) skipRest();
  }, 1000);
}

function skipRest() {
  clearInterval(restInterval);
  document.getElementById('rest-overlay').classList.add('hidden');
}

async function finishWorkout() {
  if (!confirm('Finish this workout?')) return;
  clearInterval(timerInterval);
  await api(`/api/sessions/${currentSession}/finish`, {
    method: 'PUT', body: JSON.stringify({ duration_seconds: timerSeconds })
  });
  currentSession = null;
  document.getElementById('active-workout').classList.add('hidden');
  document.getElementById('no-active').classList.remove('hidden');
  // Go to history
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelector('[data-tab="history"]').classList.add('active');
  document.getElementById('tab-history').classList.add('active');
  loadHistory();
}

function formatTime(s) { return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`; }

// ── History ──
async function loadHistory() {
  const history = await api('/api/history');
  const el = document.getElementById('history-list');
  if (history.length === 0) {
    el.innerHTML = '<div class="empty-state"><span class="empty-icon">📈</span><h2>No History Yet</h2><p>Complete a workout to see it here</p></div>';
    return;
  }
  el.innerHTML = history.map(h =>
    `<div class="history-card">
      <div class="h-info"><h3>${h.name || h.template_name || 'Workout'}</h3><div class="h-date">${new Date(h.started_at).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })} · ${formatTime(h.duration_seconds || 0)}</div></div>
      <div class="h-stats">
        <div><div class="h-stat-val">${h.completed_sets}/${h.total_sets}</div><div class="h-stat-lbl">Sets</div></div>
        <div><div class="h-stat-val">${formatVolume(h.total_volume || 0)}</div><div class="h-stat-lbl">Volume</div></div>
      </div>
    </div>`
  ).join('');
}

// ── Init ──
loadDashboard();
