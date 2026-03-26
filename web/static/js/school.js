// School Dashboard — grades, upcoming assignments, missing work

document.addEventListener('DOMContentLoaded', function() {
  // Tab switching
  document.querySelectorAll('.tab-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var tab = this.dataset.tab;

      document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
      document.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });

      this.classList.add('active');
      document.getElementById('tab-' + tab).classList.add('active');
    });
  });

  // Refresh button
  document.getElementById('refreshBtn').addEventListener('click', loadAll);

  // Initial load
  loadAll();
});

function loadAll() {
  loadGrades();
  loadUpcoming();
  loadMissing();
}

// --- Grades ---

function loadGrades() {
  var loading = document.getElementById('grades-loading');
  var content = document.getElementById('grades-content');
  var error = document.getElementById('grades-error');

  loading.style.display = 'flex';
  content.style.display = 'none';
  error.style.display = 'none';

  fetch('/api/school/grades')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      loading.style.display = 'none';

      if (data.error) {
        error.textContent = data.error;
        error.style.display = 'block';
        return;
      }

      renderGrades(data);
      content.style.display = 'block';
    })
    .catch(function(err) {
      loading.style.display = 'none';
      error.textContent = 'Failed to load grades: ' + err.message;
      error.style.display = 'block';
    });
}

function renderGrades(data) {
  var tbody = document.getElementById('grades-body');
  tbody.innerHTML = '';

  // Handle different response formats from school.py
  var grades = data.grades || data.courses || [];
  if (!Array.isArray(grades)) {
    // Try parsing as text output
    tbody.innerHTML = '<tr><td colspan="3"><pre>' + JSON.stringify(data, null, 2) + '</pre></td></tr>';
    return;
  }

  if (grades.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" class="empty-state">No grade data available.</td></tr>';
    return;
  }

  grades.forEach(function(g) {
    var tr = document.createElement('tr');

    var course = g.course || g.name || 'Unknown';
    var grade = g.grade || g.letter_grade || g.current_grade || '-';
    var score = g.score || g.current_score || g.percentage || '-';

    var gradeClass = 'grade-f';
    if (typeof grade === 'string') {
      var letter = grade.charAt(0).toUpperCase();
      if (letter === 'A') gradeClass = 'grade-a';
      else if (letter === 'B') gradeClass = 'grade-b';
      else if (letter === 'C') gradeClass = 'grade-c';
      else if (letter === 'D') gradeClass = 'grade-d';
    }

    tr.innerHTML =
      '<td>' + escapeHtml(course) + '</td>' +
      '<td><span class="grade-badge ' + gradeClass + '">' + escapeHtml(String(grade)) + '</span></td>' +
      '<td class="score-text">' + escapeHtml(String(score)) + (typeof score === 'number' ? '%' : '') + '</td>';

    tbody.appendChild(tr);
  });
}

// --- Upcoming ---

function loadUpcoming() {
  var loading = document.getElementById('upcoming-loading');
  var content = document.getElementById('upcoming-content');
  var error = document.getElementById('upcoming-error');

  loading.style.display = 'flex';
  content.style.display = 'none';
  error.style.display = 'none';

  fetch('/api/school/upcoming')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      loading.style.display = 'none';

      if (data.error) {
        error.textContent = data.error;
        error.style.display = 'block';
        return;
      }

      renderAssignments('upcoming-list', data, 'upcoming');
      content.style.display = 'block';
    })
    .catch(function(err) {
      loading.style.display = 'none';
      error.textContent = 'Failed to load upcoming: ' + err.message;
      error.style.display = 'block';
    });
}

// --- Missing ---

function loadMissing() {
  var loading = document.getElementById('missing-loading');
  var content = document.getElementById('missing-content');
  var error = document.getElementById('missing-error');

  loading.style.display = 'flex';
  content.style.display = 'none';
  error.style.display = 'none';

  fetch('/api/school/missing')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      loading.style.display = 'none';

      if (data.error) {
        error.textContent = data.error;
        error.style.display = 'block';
        return;
      }

      renderAssignments('missing-list', data, 'missing');
      content.style.display = 'block';
    })
    .catch(function(err) {
      loading.style.display = 'none';
      error.textContent = 'Failed to load missing work: ' + err.message;
      error.style.display = 'block';
    });
}

function renderAssignments(containerId, data, type) {
  var container = document.getElementById(containerId);
  container.innerHTML = '';

  var items = data.assignments || data.missing || data.upcoming || [];
  if (!Array.isArray(items)) {
    container.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
    return;
  }

  if (items.length === 0) {
    var icon = type === 'missing' ? 'check_circle' : 'event_available';
    var msg = type === 'missing' ? 'No missing work!' : 'No upcoming assignments.';
    container.innerHTML =
      '<div class="empty-state">' +
      '<span class="material-icons">' + icon + '</span>' +
      '<p>' + msg + '</p></div>';
    return;
  }

  items.forEach(function(item) {
    var name = item.name || item.assignment || 'Unknown';
    var course = item.course || item.course_name || '';
    var dueAt = item.due_at || item.due_date || '';
    var points = item.points_possible || item.points || '';
    var isOverdue = type === 'missing';

    var dueStr = '';
    if (dueAt) {
      try {
        var d = new Date(dueAt);
        dueStr = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
      } catch(e) {
        dueStr = dueAt;
      }
    }

    var div = document.createElement('div');
    div.className = 'assignment-item' + (isOverdue ? ' overdue' : '');
    div.innerHTML =
      '<div class="assignment-icon ' + type + '">' +
        '<span class="material-icons">' + (isOverdue ? 'warning' : 'assignment') + '</span>' +
      '</div>' +
      '<div class="assignment-info">' +
        '<p class="assignment-name">' + escapeHtml(name) + '</p>' +
        '<p class="assignment-meta">' + escapeHtml(course) + (dueStr ? ' &middot; ' + escapeHtml(dueStr) : '') + '</p>' +
      '</div>' +
      (points ? '<div class="assignment-points">' + escapeHtml(String(points)) + ' pts</div>' : '');

    container.appendChild(div);
  });
}

function escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
