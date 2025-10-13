<?php
$token="8378463150:AAHN1DgfNSDK9QR_RXYkyhkkgh4cEU3sQTc";
$file=__DIR__."/statdata.json";

if(!file_exists($file)) file_put_contents($file, json_encode([]));
$d = json_decode(file_get_contents($file), true);
if(!is_array($d)) $d = [];

if(!isset($d['history'])) $d['history'] = [];
if(!isset($d['users'])) $d['users'] = [];
if(!isset($d['chats'])) $d['chats'] = [];

$raw = file_get_contents("php://input");
if(!$raw && isset($GLOBALS['update'])) $raw = json_encode($GLOBALS['update']);
if($raw){
  $u = json_decode($raw, true);
  if(isset($u['message'])){
    $msg = $u['message'];
    $chat = $msg['chat'] ?? [];
    $from = $msg['from'] ?? [];
    $cid = $chat['id'] ?? 0;
    $uid = $from['id'] ?? 0;
    $dateHour = date('Y-m-d H');

    if(!isset($d['history'][$dateHour])) $d['history'][$dateHour] = ['msgs'=>0,'users'=>[],'user_msgs'=>[],'chat_msgs'=>[]];

    $d['history'][$dateHour]['msgs']++;

    if(!in_array($uid, $d['history'][$dateHour]['users'])) $d['history'][$dateHour]['users'][] = $uid;

    if(!isset($d['history'][$dateHour]['user_msgs'][$uid])) $d['history'][$dateHour]['user_msgs'][$uid] = 0;
    $d['history'][$dateHour]['user_msgs'][$uid]++;

    if(!isset($d['history'][$dateHour]['chat_msgs'][$cid])) $d['history'][$dateHour]['chat_msgs'][$cid] = 0;
    $d['history'][$dateHour]['chat_msgs'][$cid]++;

    if(!isset($d['chats'][$cid])){
      $d['chats'][$cid] = [
        'type' => $chat['type'] ?? 'private',
        'title' => $chat['title'] ?? ($chat['first_name'] ?? ('chat_'.$cid)),
        'username' => $chat['username'] ?? null,
        'msgs' => 0
      ];
    }
    $d['chats'][$cid]['msgs']++;

    if(!isset($d['users'][$uid])){
      $d['users'][$uid] = [
        'first_name' => $from['first_name'] ?? '',
        'last_name' => $from['last_name'] ?? '',
        'username' => $from['username'] ?? null,
        'msgs' => 0,
        'first_seen' => time()
      ];
    }
    $d['users'][$uid]['msgs']++;

    $f = fopen($file,'c+');
    if($f){
      flock($f, LOCK_EX);
      ftruncate($f, 0);
      fwrite($f, json_encode($d, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE));
      fflush($f);
      flock($f, LOCK_UN);
      fclose($f);
    }
  }
}

if(isset($_GET['mode'])){
  $m = $_GET['mode'];
  $now = time();
  $grouped = [];

  foreach($d['history'] as $hourKey => $slot){
    $ts = strtotime($hourKey.":00:00");
    if($m === 'day'){
      if($now - $ts <= 86400) {
        $grouped[$hourKey] = $slot;
      }
    } elseif($m === 'week' || $m === 'month' || $m === 'all'){
      $day = date('Y-m-d', $ts);
      if(!isset($grouped[$day])) $grouped[$day] = ['msgs'=>0,'users'=>[],'user_msgs'=>[],'chat_msgs'=>[]];
      $grouped[$day]['msgs'] += $slot['msgs'];
      $grouped[$day]['users'] = array_values(array_unique(array_merge($grouped[$day]['users'],$slot['users'])));
      foreach($slot['user_msgs'] as $uid => $cnt){
        if(!isset($grouped[$day]['user_msgs'][$uid])) $grouped[$day]['user_msgs'][$uid] = 0;
        $grouped[$day]['user_msgs'][$uid] += $cnt;
      }
      foreach($slot['chat_msgs'] as $cid => $cmsg){
        if(!isset($grouped[$day]['chat_msgs'][$cid])) $grouped[$day]['chat_msgs'][$cid] = 0;
        $grouped[$day]['chat_msgs'][$cid] += $cmsg;
      }
    }
  }

  if($m === 'week'){
    $filtered = [];
    foreach($grouped as $k=>$v){
      if($now - strtotime($k.' 00:00:00') <= 7*86400) $filtered[$k] = $v;
    }
    $grouped = $filtered;
  } elseif($m === 'month'){
    $filtered = [];
    foreach($grouped as $k=>$v){
      if($now - strtotime($k.' 00:00:00') <= 30*86400) $filtered[$k] = $v;
    }
    $grouped = $filtered;
  } elseif($m === 'all'){
  }

  ksort($grouped);
  $labels = array_keys($grouped);
  $msgs = array_map(fn($x)=>$x['msgs'], $grouped);
  $usersCount = array_map(fn($x)=>count($x['users']), $grouped);

  $allUsersList = [];
  $todayUsersList = [];
  $todayMsgs = 0;
  foreach($d['history'] as $hk => $slot){
    $ts = strtotime($hk.":00:00");
    $allUsersList = array_merge($allUsersList, $slot['users']);
    if($now - $ts <= 86400){
      $todayUsersList = array_merge($todayUsersList, $slot['users']);
      $todayMsgs += $slot['msgs'];
    }
  }
  $summary = [
    'totalUsers' => count(array_unique($allUsersList)),
    'new24h' => count(array_unique($todayUsersList)),
    'msgs24h' => $todayMsgs
  ];

  $groupChats = 0;
  $groupMsgsTotal = 0;
  $topGroup = null;
  foreach($d['chats'] as $cid => $cinfo){
    $type = strtolower($cinfo['type'] ?? '');
    if(in_array($type, ['group','supergroup'])){
      $groupChats++;
      $groupMsgsTotal += ($cinfo['msgs'] ?? 0);
      if($topGroup === null || ($cinfo['msgs'] ?? 0) > ($topGroup['msgs'] ?? 0)){
        $topGroup = [
          'id' => $cid,
          'title' => $cinfo['title'] ?? ('group_'.$cid),
          'username' => $cinfo['username'] ?? null,
          'msgs' => $cinfo['msgs'] ?? 0
        ];
      }
    }
  }

  $topUsers = [];
  foreach($d['users'] as $uid => $uinfo){
    $topUsers[$uid] = [
      'id' => $uid,
      'first_name' => $uinfo['first_name'] ?? '',
      'last_name' => $uinfo['last_name'] ?? '',
      'username' => $uinfo['username'] ?? null,
      'msgs' => $uinfo['msgs'] ?? 0,
      'first_seen' => $uinfo['first_seen'] ?? null
    ];
  }
  uasort($topUsers, function($a,$b){ return ($b['msgs'] <=> $a['msgs']); });
  $topUsers = array_values($topUsers);

  $user24 = [];
  foreach($d['history'] as $hk => $slot){
    $ts = strtotime($hk.":00:00");
    if($now - $ts <= 86400){
      if(!empty($slot['user_msgs'])){
        foreach($slot['user_msgs'] as $uid => $cnt){
          if(!isset($user24[$uid])) $user24[$uid] = 0;
          $user24[$uid] += $cnt;
        }
      }
    }
  }

  foreach($topUsers as $k => $u){
    $uid = $u['id'];
    $topUsers[$k]['msgs24h'] = isset($user24[$uid]) ? $user24[$uid] : 0;
    $topUsers[$k]['first_seen_readable'] = $u['first_seen'] ? date('Y-m-d H:i:s', $u['first_seen']) : null;
  }

  $resp = [
    'labels' => $labels,
    'msgs' => $msgs,
    'users' => $usersCount,
    'summary' => $summary,
    'groups' => [
      'total_groups' => $groupChats,
      'group_msgs_total' => $groupMsgsTotal,
      'top_group' => $topGroup
    ],
    'topUsers' => array_slice($topUsers, 0, 10)
  ];

  header('Content-Type: application/json; charset=utf-8');
  echo json_encode($resp, JSON_UNESCAPED_UNICODE);
  exit;
}
?>
<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>StatPanel</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{
  --glass-bg: rgba(255,255,255,0.06);
  --glass-border: rgba(255,255,255,0.12);
  --muted: #a5b4fc;
  --accent: #38bdf8;
}
body{
  font-family:'Poppins',sans-serif;
  margin:0;padding:20px;
  min-height:100vh;
  background:linear-gradient(135deg,#071020,#0b2b66 40%,#08112a);
  color:#fff;
  display:flex;align-items:center;justify-content:center;
}
.container{
  width:100%;max-width:1100px;display:flex;flex-direction:column;gap:18px;
  padding:18px;
  border-radius:18px;
  background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  box-shadow: 0 10px 40px rgba(2,6,23,0.6);
}
header{display:flex;align-items:center;justify-content:space-between;gap:10px}
h1{margin:0;font-size:1.3rem;cursor:pointer;color:#fff}
.header-right{font-size:.9rem;color:var(--muted)}

.summary{
  display:flex;gap:10px;justify-content:space-between;align-items:center;
  background:var(--glass-bg);
  border:1px solid var(--glass-border);
  backdrop-filter: blur(18px);
  padding:8px;border-radius:14px;
}
.summary-item{
  flex:1;min-width:0;padding:10px;border-radius:12px;text-align:center;
  background:linear-gradient(180deg, rgba(255,255,255,0.02), transparent);
}
.summary-item h3{margin:0;font-size:.85rem;color:var(--muted);font-weight:500}
.summary-item p{margin:6px 0 0;font-size:1.05rem;font-weight:700;color:#fff}

.controls{display:flex;gap:10px;flex-wrap:wrap;justify-content:center}
button{
  background:transparent;border:1px solid rgba(255,255,255,0.08);padding:8px 14px;border-radius:12px;color:#fff;cursor:pointer;
}
button.active{border-color:var(--accent);box-shadow:0 6px 18px rgba(56,189,248,0.08);transform:translateY(-1px)}

.chart-wrap{
  background: rgba(255,255,255,0.03);
  border-radius:16px;padding:16px;border:1px solid rgba(255,255,255,0.06);
  backdrop-filter: blur(12px);
}
canvas{width:100%!important;height:320px!important}

.extra{
  display:flex;gap:16px;flex-wrap:wrap;
}
.panel{
  flex:1;min-width:260px;
  background:rgba(255,255,255,0.03);border-radius:14px;padding:12px;border:1px solid rgba(255,255,255,0.05);
  backdrop-filter: blur(10px);
}
.panel h4{margin:0 0 8px;font-size:0.95rem;color:var(--muted)}
.group-list, .user-list{display:flex;flex-direction:column;gap:8px}
.group-item, .user-item{
  padding:8px;border-radius:10px;background:linear-gradient(180deg, rgba(255,255,255,0.01), transparent);
  border:1px solid rgba(255,255,255,0.03);cursor:pointer;
}
.small{font-size:.85rem;color:#cbd5e1}
.user-detail{margin-top:8px;padding:8px;border-radius:10px;background:rgba(0,0,0,0.15);font-size:.9rem}

@media(max-width:720px){
  .summary{flex-direction:row}
  .extra{flex-direction:column}
}
footer{font-size:.85rem;color:#94a3b8;text-align:center;margin-top:8px}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1 onclick="window.open('https://ozodbekdev.uz','_blank')">📊 StatPanel</h1>
    <div class="header-right">StatPanel — OzodbekDev</div>
  </header>

  <div class="summary">
    <div class="summary-item"><h3>Jami foydalanuvchilar</h3><p id="totalUsers">0</p></div>
    <div class="summary-item"><h3>Yangi (24 soat)</h3><p id="new24h">0</p></div>
    <div class="summary-item"><h3>Xabarlar (24 soat)</h3><p id="msgs24h">0</p></div>
  </div>

  <div class="controls">
    <button id="b-day" class="active" onclick="setMode('day')">Kunlik</button>
    <button id="b-week" onclick="setMode('week')">Haftalik</button>
    <button id="b-month" onclick="setMode('month')">Oylik</button>
    <button id="b-all" onclick="setMode('all')">Umumiy</button>

    <div style="width:8px"></div>

    <button id="s-line" class="active" onclick="setStyle('line')">Chiziqli</button>
    <button id="s-bar" onclick="setStyle('bar')">Ustunli</button>
  </div>

  <div class="chart-wrap">
    <canvas id="chart"></canvas>
  </div>

  <div class="extra">
    <div class="panel">
      <h4>Guruhlar</h4>
      <div class="group-list" id="groupPanel">
        <div class="small">Yuklanmoqda...</div>
      </div>
    </div>

    <div class="panel">
      <h4>Eng faol a'zolar (Top 3)</h4>
      <div class="user-list" id="userPanel">
        <div class="small">Yuklanmoqda...</div>
      </div>
    </div>
  </div>

  <footer>© 2025 OzodbekDev — StatPanel</footer>
</div>

<script>
let chartType = localStorage.getItem('chartType') || 'line';
let chart = null;
let currentMode = 'day';

function setStyle(t){
  document.querySelectorAll('#s-line,#s-bar').forEach(b=>b.classList.remove('active'));
  document.getElementById('s-' + (t==='line'?'line':'bar')).classList.add('active');
  chartType = t;
  localStorage.setItem('chartType', t);
  loadData(currentMode);
}

function setMode(m){
  currentMode = m;
  document.querySelectorAll('#b-day,#b-week,#b-month,#b-all').forEach(b=>b.classList.remove('active'));
  document.getElementById('b-' + (m==='day'?'day':(m==='week'?'week':(m==='month'?'month':'all')))).classList.add('active');
  loadData(m);
}

async function loadData(mode){
  const res = await fetch(`?mode=${mode}`);
  const j = await res.json();

  document.getElementById('totalUsers').innerText = j.summary.totalUsers;
  document.getElementById('new24h').innerText = j.summary.new24h;
  document.getElementById('msgs24h').innerText = j.summary.msgs24h;

  const ctx = document.getElementById('chart').getContext('2d');
  if(chart) chart.destroy();
  chart = new Chart(ctx, {
    type: chartType,
    data: {
      labels: j.labels.map(x=>x.replace(' ','\n')),
      datasets: [
        {
          label: 'Xabarlar',
          data: j.msgs,
          borderColor: '#38bdf8',
          backgroundColor: chartType==='bar' ? '#38bdf880' : '#38bdf830',
          fill: chartType!=='bar',
          tension: 0.35
        },
        {
          label: 'Foydalanuvchilar',
          data: j.users,
          borderColor: '#22c55e',
          backgroundColor: chartType==='bar' ? '#22c55e80' : '#22c55e30',
          fill: chartType!=='bar',
          tension: 0.35
        }
      ]
    },
    options:{
      responsive:true,
      plugins:{legend:{labels:{color:'#fff'}}},
      scales:{x:{ticks:{color:'#a5b4fc'}},y:{ticks:{color:'#a5b4fc'}}}
    }
  });

  const gp = document.getElementById('groupPanel');
  gp.innerHTML = '';
  const groups = j.groups || {};
  const totalGroups = groups.total_groups ?? 0;
  const groupMsgs = groups.group_msgs_total ?? 0;
  const topGroup = groups.top_group ?? null;

  const nodeInfo = document.createElement('div');
  nodeInfo.className = 'small';
  nodeInfo.innerHTML = `<div>Bot admin bo‘lgan guruhlar: <strong>${totalGroups}</strong></div>
                        <div>Guruhlardagi jami xabarlar: <strong>${groupMsgs}</strong></div>`;
  gp.appendChild(nodeInfo);

  if(topGroup){
    const tg = document.createElement('div');
    tg.className = 'group-item';
    const uname = topGroup.username ? ` (@${topGroup.username})` : '';
    tg.innerHTML = `<strong>Eng faol guruh:</strong><div style="margin-top:6px">${escapeHtml(topGroup.title)}${uname}</div><div class="small" style="margin-top:6px">Xabarlar: <strong>${topGroup.msgs}</strong></div>`;
    gp.appendChild(tg);
  }

  const up = document.getElementById('userPanel');
  up.innerHTML = '';
  const topUsers = (j.topUsers || []).slice(0,3);
  if(topUsers.length === 0){
    up.innerHTML = '<div class="small">Ma\'lumot topilmadi</div>';
  } else {
    topUsers.forEach((u, idx) => {
      const div = document.createElement('div');
      div.className = 'user-item';
      const name = (u.first_name || '') + (u.last_name ? ' ' + u.last_name : '');
      const username = u.username ? `@${u.username}` : '';
      div.innerHTML = `<div><strong>#${idx+1} ${escapeHtml(name || username || 'No name')}</strong> <span class="small">(${u.id})</span></div>
                       <div class="small">Jami xabarlar: <strong>${u.msgs}</strong> — 24 soat: <strong>${u.msgs24h}</strong></div>`;
      const detail = document.createElement('div');
      detail.className = 'user-detail';
      detail.style.display = 'none';
      detail.innerHTML = `<div><strong>Qo'shilgan:</strong> ${u.first_seen_readable ?? '—'}</div>
                          <div><strong>Ismi:</strong> ${escapeHtml(name || '—')}</div>
                          <div><strong>Username:</strong> ${escapeHtml(username || '—')}</div>
                          <div><strong>ID:</strong> ${u.id}</div>
                          <div><strong>Jami xabarlar:</strong> ${u.msgs}</div>
                          <div><strong>24 soat ichidagi xab:</strong> ${u.msgs24h}</div>`;
      div.appendChild(detail);
      div.addEventListener('click', ()=> {
        detail.style.display = (detail.style.display === 'none') ? 'block' : 'none';
      });
      up.appendChild(div);
    });
  }
}

function escapeHtml(s){
  if(!s) return '';
  return String(s).replace(/[&<>"']/g, function(m){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]; });
}

setStyle(chartType);
setMode('day');
</script>
</body>
</html>