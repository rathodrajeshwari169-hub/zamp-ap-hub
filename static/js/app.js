// Zamp AP Hub - Frontend Client Engine

let currentTab = 'live-run';
let currentRunResult = null;
let activeEventSource = null;

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
    loadRunsHistory('ALL');
    loadPOs();
    loadVendors();
});

// -------------------------------------------------------------
// Navigation & Tab Switching
// -------------------------------------------------------------
function switchTab(tabId) {
    currentTab = tabId;
    ['live-run', 'dashboard', 'pos', 'vendors'].forEach(t => {
        const section = document.getElementById(`tab-${t}`);
        const btn = document.getElementById(`tab-btn-${t}`);
        if (t === tabId) {
            section.classList.remove('hidden');
            btn.classList.add('bg-white', 'shadow-sm', 'text-sky-700', 'font-semibold');
            btn.classList.remove('text-slate-600');
        } else {
            section.classList.add('hidden');
            btn.classList.remove('bg-white', 'shadow-sm', 'text-sky-700', 'font-semibold');
            btn.classList.add('text-slate-600');
        }
    });

    if (tabId === 'dashboard') {
        loadDashboardStats();
        loadRunsHistory('ALL');
    } else if (tabId === 'pos') {
        loadPOs();
    } else if (tabId === 'vendors') {
        loadVendors();
    }
}

// -------------------------------------------------------------
// Live Run View & Stepper Execution
// -------------------------------------------------------------
function resetStepperUI() {
    for (let i = 1; i <= 5; i++) {
        const card = document.getElementById(`stage-card-${i}`);
        const icon = document.getElementById(`stage-icon-${i}`);
        const status = document.getElementById(`stage-status-${i}`);
        const duration = document.getElementById(`stage-duration-${i}`);

        card.className = 'stage-node bg-slate-50 border border-slate-200 rounded-xl p-4 transition-all';
        icon.className = 'w-6 h-6 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center text-xs';
        status.textContent = 'Idle';
        duration.textContent = '--';
    }
    const badge = document.getElementById('pipeline-status-badge');
    badge.className = 'px-3 py-1 rounded-full text-xs font-semibold bg-sky-100 text-sky-800 border border-sky-200 animate-pulse';
    badge.textContent = 'Executing Pipeline...';

    const consoleDiv = document.getElementById('live-console');
    consoleDiv.innerHTML = '<div class="text-slate-500">// Pipeline started. Streaming live audit trace...</div>';

    document.getElementById('execution-results-container').classList.add('hidden');
}

function logToConsole(message, type = 'info') {
    const consoleDiv = document.getElementById('live-console');
    const timeStr = new Date().toISOString().substring(11, 23);
    const color = type === 'error' ? 'text-rose-400' : (type === 'warn' ? 'text-amber-300' : (type === 'success' ? 'text-emerald-400' : 'text-slate-300'));
    const entry = document.createElement('div');
    entry.className = `${color} leading-relaxed`;
    entry.textContent = `[${timeStr}] ${message}`;
    consoleDiv.appendChild(entry);
    consoleDiv.scrollTop = consoleDiv.scrollHeight;
}

function runScenario(sampleId) {
    if (activeEventSource) {
        activeEventSource.close();
    }
    resetStepperUI();
    logToConsole(`Initiating scenario run: [${sampleId}]`, 'info');

    // Highlight active stage 1
    updateStageActive(1);

    activeEventSource = new EventSource(`/api/stream_process?sample_id=${sampleId}`);

    activeEventSource.onmessage = function (event) {
        const data = JSON.parse(event.data);

        if (data.event === 'start') {
            logToConsole(`File ingested: ${data.filename}`, 'info');
        } else if (data.event === 'stage_complete') {
            const stage = data.stage;
            updateStageFinished(stage);
            logToConsole(`Stage ${stage.stage_number} [${stage.stage_name}]: ${stage.summary} (${stage.duration_ms}ms)`, stage.status === 'FAILED' ? 'error' : (stage.status === 'WARNING' ? 'warn' : 'success'));
            
            // Activate next stage if exists
            if (stage.stage_number < 5) {
                updateStageActive(stage.stage_number + 1);
            }
        } else if (data.event === 'final_decision') {
            activeEventSource.close();
            activeEventSource = null;
            currentRunResult = data.result;

            const badge = document.getElementById('pipeline-status-badge');
            badge.className = 'px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200';
            badge.textContent = `Completed (${currentRunResult.latency_ms}ms)`;

            logToConsole(`Pipeline Complete! Final Decision: ${currentRunResult.status} [${currentRunResult.decision_type}] in ${currentRunResult.latency_ms}ms`, 'success');

            renderExecutionResults(currentRunResult);
            loadDashboardStats();
        }
    };

    activeEventSource.onerror = function () {
        logToConsole(`Stream connection closed.`, 'info');
        if (activeEventSource) {
            activeEventSource.close();
            activeEventSource = null;
        }
    };
}

function updateStageActive(stageNum) {
    const card = document.getElementById(`stage-card-${stageNum}`);
    const icon = document.getElementById(`stage-icon-${stageNum}`);
    const status = document.getElementById(`stage-status-${stageNum}`);

    card.className = 'stage-node bg-sky-50 border-2 border-sky-400 rounded-xl p-4 shadow-md shadow-sky-100 pulse-step';
    icon.className = 'w-6 h-6 rounded-full bg-sky-600 text-white flex items-center justify-center text-xs animate-spin';
    icon.innerHTML = '<i class="fa-solid fa-spinner"></i>';
    status.textContent = 'Processing...';
}

function updateStageFinished(stage) {
    const i = stage.stage_number;
    const card = document.getElementById(`stage-card-${i}`);
    const icon = document.getElementById(`stage-icon-${i}`);
    const status = document.getElementById(`stage-status-${i}`);
    const duration = document.getElementById(`stage-duration-${i}`);

    duration.textContent = `${stage.duration_ms}ms`;

    if (stage.status === 'COMPLETED') {
        card.className = 'stage-node bg-white border border-emerald-300 rounded-xl p-4 shadow-sm';
        icon.className = 'w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center text-xs';
        icon.innerHTML = '<i class="fa-solid fa-check"></i>';
        status.textContent = 'Passed';
        status.className = 'text-emerald-700 font-semibold';
    } else if (stage.status === 'WARNING') {
        card.className = 'stage-node bg-white border border-amber-300 rounded-xl p-4 shadow-sm';
        icon.className = 'w-6 h-6 rounded-full bg-amber-500 text-white flex items-center justify-center text-xs';
        icon.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
        status.textContent = 'Warning';
        status.className = 'text-amber-700 font-semibold';
    } else { // FAILED
        card.className = 'stage-node bg-white border border-rose-300 rounded-xl p-4 shadow-sm';
        icon.className = 'w-6 h-6 rounded-full bg-rose-500 text-white flex items-center justify-center text-xs';
        icon.innerHTML = '<i class="fa-solid fa-xmark"></i>';
        status.textContent = 'Flagged';
        status.className = 'text-rose-700 font-semibold';
    }
}

// -------------------------------------------------------------
// Render Execution Results
// -------------------------------------------------------------
function renderExecutionResults(res) {
    const container = document.getElementById('execution-results-container');
    container.classList.remove('hidden');

    const banner = document.getElementById('decision-banner-card');
    const badgeIcon = document.getElementById('decision-badge-icon');
    const titleText = document.getElementById('decision-title-text');
    const subtitle = document.getElementById('decision-type-subtitle');
    const confidence = document.getElementById('decision-confidence-pill');
    const explanation = document.getElementById('decision-explanation-text');
    const action = document.getElementById('decision-action-text');

    confidence.textContent = `Confidence: ${Math.round(res.confidence_score * 100)}%`;
    explanation.textContent = res.summary;
    action.textContent = res.recommended_action;

    if (res.status === 'APPROVED') {
        banner.className = 'bg-white border-2 border-emerald-400 rounded-2xl p-6 shadow-sm';
        badgeIcon.className = 'w-12 h-12 rounded-xl bg-emerald-500 text-white flex items-center justify-center text-xl shadow-md shadow-emerald-200';
        badgeIcon.innerHTML = '<i class="fa-solid fa-check-double"></i>';
        titleText.textContent = res.decision_type.replace(/_/g, ' ');
        titleText.className = 'text-xl font-bold tracking-tight text-emerald-800';
        subtitle.textContent = 'Cleared for Autonomous ERP Disbursement';
    } else if (res.status === 'NEEDS_REVIEW') {
        banner.className = 'bg-white border-2 border-amber-400 rounded-2xl p-6 shadow-sm';
        badgeIcon.className = 'w-12 h-12 rounded-xl bg-amber-500 text-white flex items-center justify-center text-xl shadow-md shadow-amber-200';
        badgeIcon.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
        titleText.textContent = res.decision_type.replace(/_/g, ' ');
        titleText.className = 'text-xl font-bold tracking-tight text-amber-800';
        subtitle.textContent = 'Human-in-the-Loop AP Review Required';
    } else { // REJECTED
        banner.className = 'bg-white border-2 border-rose-400 rounded-2xl p-6 shadow-sm';
        badgeIcon.className = 'w-12 h-12 rounded-xl bg-rose-500 text-white flex items-center justify-center text-xl shadow-md shadow-rose-200';
        badgeIcon.innerHTML = '<i class="fa-solid fa-ban"></i>';
        titleText.textContent = res.decision_type.replace(/_/g, ' ');
        titleText.className = 'text-xl font-bold tracking-tight text-rose-800';
        subtitle.textContent = 'Blocked by Compliance or Duplicate Rules';
    }

    // Email Preview
    const emailContainer = document.getElementById('email-preview-container');
    if (res.vendor_email_draft) {
        emailContainer.textContent = `Subject: ${res.vendor_email_draft.subject}\n\n${res.vendor_email_draft.body}`;
    }

    // Extracted Metadata
    const ext = res.extracted_data;
    document.getElementById('meta-vendor-name').textContent = ext.vendor_name || 'UNRESOLVED';
    document.getElementById('meta-invoice-number').textContent = ext.invoice_number || 'MISSING';
    document.getElementById('meta-invoice-date').textContent = ext.invoice_date || 'N/A';
    document.getElementById('meta-invoice-total').textContent = `$${(ext.total_amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    const bank = ext.remittance_bank || {};
    document.getElementById('meta-bank-routing').textContent = `Routing: ${bank.routing_number || 'N/A'} | Acct: ${bank.account_number ? '****' + bank.account_number.slice(-4) : 'N/A'}`;

    // Reconciliation Bar
    const match = res.match_result;
    const po = match.po;
    const reconBadge = document.getElementById('reconciliation-badge');
    const poLabel = document.getElementById('reconcile-po-label');
    const poAmounts = document.getElementById('reconcile-po-amounts');

    if (po) {
        reconBadge.textContent = match.match_type.replace(/_/g, ' ');
        reconBadge.className = 'text-xs font-semibold px-2 py-0.5 rounded-full bg-sky-100 text-sky-800 border border-sky-200';
        poLabel.textContent = `Matched ${po.po_number} (${po.description})`;

        const poTotal = po.total_amount;
        const priorBilled = po.previously_invoiced;
        const currentBilled = ext.total_amount;
        const remaining = Math.max(0, poTotal - priorBilled - currentBilled);

        poAmounts.textContent = `Budget: $${poTotal.toLocaleString()} | Stated: $${currentBilled.toLocaleString()}`;

        const priorPct = Math.min(100, (priorBilled / poTotal) * 100);
        const currPct = Math.min(100 - priorPct, (currentBilled / poTotal) * 100);

        document.getElementById('po-bar-prior').style.width = `${priorPct}%`;
        document.getElementById('po-bar-current').style.width = `${currPct}%`;

        document.getElementById('po-label-prior').textContent = `Prior: $${priorBilled.toLocaleString()}`;
        document.getElementById('po-label-current').textContent = `This Inv: $${currentBilled.toLocaleString()}`;
        document.getElementById('po-label-remaining').textContent = `Remaining Balance: $${remaining.toLocaleString()}`;
    } else {
        reconBadge.textContent = 'NO PO MATCHED';
        reconBadge.className = 'text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-200';
        poLabel.textContent = 'No Purchase Order Matched';
        poAmounts.textContent = 'Stated: $' + (ext.total_amount || 0).toLocaleString();
        document.getElementById('po-bar-prior').style.width = '0%';
        document.getElementById('po-bar-current').style.width = '0%';
        document.getElementById('po-label-prior').textContent = 'Prior: $0.00';
        document.getElementById('po-label-current').textContent = 'This Inv: $' + (ext.total_amount || 0).toLocaleString();
        document.getElementById('po-label-remaining').textContent = 'Unmatched';
    }

    // Line Items Table
    const tbody = document.getElementById('line-items-tbody');
    tbody.innerHTML = '';
    const lineRecon = match.line_reconciliation || [];
    if (lineRecon.length === 0 && ext.line_items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="p-4 text-center text-slate-400 italic">No line items extracted from document</td></tr>';
    } else if (lineRecon.length > 0) {
        lineRecon.forEach(item => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-50';
            const matchedPill = item.matched 
                ? '<span class="bg-emerald-100 text-emerald-800 text-[10px] px-2 py-0.5 rounded-full font-bold">100% Matched</span>'
                : '<span class="bg-slate-100 text-slate-600 text-[10px] px-2 py-0.5 rounded-full">Unmatched</span>';

            tr.innerHTML = `
                <td class="p-2.5 font-medium text-slate-800">${item.invoice_item.description}</td>
                <td class="p-2.5 text-center text-slate-600">${item.invoice_item.quantity}</td>
                <td class="p-2.5 text-right font-mono text-slate-700">$${item.invoice_item.unit_price.toFixed(2)}</td>
                <td class="p-2.5 text-right font-mono font-bold text-slate-900">$${item.invoice_item.total.toFixed(2)}</td>
                <td class="p-2.5 text-center">${matchedPill}</td>
            `;
            tbody.appendChild(tr);
        });
    } else {
        ext.line_items.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="p-2.5 font-medium text-slate-800">${item.description}</td>
                <td class="p-2.5 text-center text-slate-600">${item.quantity}</td>
                <td class="p-2.5 text-right font-mono text-slate-700">$${item.unit_price.toFixed(2)}</td>
                <td class="p-2.5 text-right font-mono font-bold text-slate-900">$${item.total.toFixed(2)}</td>
                <td class="p-2.5 text-center"><span class="bg-slate-100 text-slate-600 text-[10px] px-2 py-0.5 rounded-full">No PO Line</span></td>
            `;
            tbody.appendChild(tr);
        });
    }

    // 6-Rule Checklist
    const rulesContainer = document.getElementById('rules-checklist-container');
    rulesContainer.innerHTML = '';
    const rules = res.rule_evaluations || [];
    rules.forEach(rule => {
        const item = document.createElement('div');
        let iconHtml = '';
        let badgeClass = '';

        if (rule.status === 'PASS') {
            iconHtml = '<i class="fa-solid fa-circle-check text-emerald-600"></i>';
            badgeClass = 'bg-emerald-50 text-emerald-800 border-emerald-200';
        } else if (rule.status === 'WARN') {
            iconHtml = '<i class="fa-solid fa-triangle-exclamation text-amber-600"></i>';
            badgeClass = 'bg-amber-50 text-amber-800 border-amber-200';
        } else {
            iconHtml = '<i class="fa-solid fa-circle-xmark text-rose-600"></i>';
            badgeClass = 'bg-rose-50 text-rose-800 border-rose-200';
        }

        item.className = `p-3 rounded-xl border text-xs flex items-start justify-between space-x-3 ${badgeClass}`;
        item.innerHTML = `
            <div class="flex items-start space-x-2">
                <span class="mt-0.5">${iconHtml}</span>
                <div>
                    <span class="font-bold text-slate-900">${rule.rule_name}</span>
                    <p class="text-slate-600 text-[11px] mt-0.5 leading-relaxed">${rule.message}</p>
                </div>
            </div>
            <span class="font-bold text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-white/80 border border-slate-200">${rule.status}</span>
        `;
        rulesContainer.appendChild(item);
    });

    // Scroll smoothly to results
    container.scrollIntoView({ behavior: 'smooth' });
}

function toggleEmailPreview() {
    const el = document.getElementById('email-preview-container');
    const chevron = document.getElementById('email-toggle-chevron');
    if (el.classList.contains('hidden')) {
        el.classList.remove('hidden');
        chevron.classList.add('rotate-180');
    } else {
        el.classList.add('hidden');
        chevron.classList.remove('rotate-180');
    }
}

// -------------------------------------------------------------
// Custom File Upload
// -------------------------------------------------------------
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    document.getElementById('upload-filename').textContent = `Uploaded: ${file.name}`;
    resetStepperUI();
    logToConsole(`Uploading custom invoice: ${file.name} (${Math.round(file.size / 1024)} KB)...`, 'info');

    const formData = new FormData();
    formData.append('file', file);

    updateStageActive(1);

    fetch('/api/process', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(res => {
        if (res.error) {
            logToConsole(`Upload error: ${res.error}`, 'error');
            return;
        }
        res.stage_logs.forEach(stage => {
            updateStageFinished(stage);
            logToConsole(`Stage ${stage.stage_number} [${stage.stage_name}]: ${stage.summary}`, stage.status === 'FAILED' ? 'error' : (stage.status === 'WARNING' ? 'warn' : 'success'));
        });
        currentRunResult = res;
        renderExecutionResults(res);
        loadDashboardStats();
    })
    .catch(err => {
        logToConsole(`Error processing file: ${err}`, 'error');
    });
}

// -------------------------------------------------------------
// AP Executive Dashboard Data
// -------------------------------------------------------------
function loadDashboardStats() {
    fetch('/api/stats')
        .then(r => r.json())
        .then(stats => {
            document.getElementById('kpi-total-runs').textContent = stats.total_runs;
            document.getElementById('kpi-touchless-rate').textContent = `${stats.touchless_rate}%`;
            document.getElementById('kpi-total-value').textContent = `$${stats.total_value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            document.getElementById('kpi-review-count').textContent = stats.review;
            document.getElementById('kpi-rejected-count').textContent = stats.rejected;
            document.getElementById('kpi-avg-latency').textContent = `${stats.avg_latency} ms`;
        });
}

function loadRunsHistory(statusFilter = 'ALL') {
    fetch(`/api/runs?status=${statusFilter}`)
        .then(r => r.json())
        .then(data => {
            const tbody = document.getElementById('runs-history-tbody');
            tbody.innerHTML = '';

            if (data.runs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="p-6 text-center text-slate-400 italic">No runs found for this filter</td></tr>';
                return;
            }

            data.runs.forEach(r => {
                const tr = document.createElement('tr');
                tr.className = 'hover:bg-slate-50 transition-colors';

                let badge = '';
                if (r.status === 'APPROVED') {
                    badge = '<span class="bg-emerald-100 text-emerald-800 text-[10px] px-2.5 py-0.5 rounded-full font-bold">APPROVED</span>';
                } else if (r.status === 'NEEDS_REVIEW') {
                    badge = '<span class="bg-amber-100 text-amber-800 text-[10px] px-2.5 py-0.5 rounded-full font-bold">NEEDS REVIEW</span>';
                } else {
                    badge = '<span class="bg-rose-100 text-rose-800 text-[10px] px-2.5 py-0.5 rounded-full font-bold">REJECTED</span>';
                }

                tr.innerHTML = `
                    <td class="p-3">
                        <span class="font-mono text-slate-700 font-semibold block">${r.run_id}</span>
                        <span class="text-[10px] text-slate-400">${r.timestamp ? r.timestamp.replace('T', ' ').replace('Z', '') : ''}</span>
                    </td>
                    <td class="p-3 font-bold text-slate-800 font-mono">${r.invoice_number || 'N/A'}</td>
                    <td class="p-3 text-slate-700 font-medium">${r.vendor_name || 'Unregistered'}</td>
                    <td class="p-3 font-mono text-slate-600">${r.po_number || 'None'}</td>
                    <td class="p-3 text-right font-mono font-bold text-slate-900">$${(r.invoice_total || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    <td class="p-3 text-center">${badge}</td>
                    <td class="p-3 text-center text-slate-500 font-mono text-[11px]">${r.latency_ms || 350}ms</td>
                    <td class="p-3 text-center">
                        <button onclick="viewRunAuditModal('${r.run_id}')" class="text-sky-600 hover:text-sky-800 bg-sky-50 hover:bg-sky-100 px-2.5 py-1 rounded-md text-[11px] font-semibold border border-sky-200">
                            <i class="fa-solid fa-eye mr-1"></i> Audit Trail
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        });
}

function filterRuns(status) {
    ['ALL', 'APPROVED', 'NEEDS_REVIEW', 'REJECTED'].forEach(s => {
        const btn = document.getElementById(`filter-btn-${s}`);
        if (s === status) {
            btn.className = 'filter-chip px-3 py-1 rounded-lg bg-sky-600 text-white font-semibold';
        } else {
            btn.className = 'filter-chip px-3 py-1 rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200';
        }
    });
    loadRunsHistory(status);
}

// -------------------------------------------------------------
// PO Explorer & Vendor Registry
// -------------------------------------------------------------
function loadPOs() {
    fetch('/api/pos')
        .then(r => r.json())
        .then(data => {
            const grid = document.getElementById('pos-grid');
            grid.innerHTML = '';
            data.purchase_orders.forEach(po => {
                const card = document.createElement('div');
                card.className = 'bg-slate-50 border border-slate-200 rounded-xl p-5 hover:border-slate-300 transition-all shadow-2xs';

                const total = po.total_amount;
                const invoiced = po.previously_invoiced;
                const remaining = po.remaining_balance;
                const pct = Math.min(100, (invoiced / total) * 100);

                let statusBadge = '<span class="bg-emerald-100 text-emerald-800 text-[10px] px-2 py-0.5 rounded-full font-bold">OPEN</span>';
                if (po.status === 'PARTIALLY_INVOICED') {
                    statusBadge = '<span class="bg-sky-100 text-sky-800 text-[10px] px-2 py-0.5 rounded-full font-bold">PARTIAL DRAW</span>';
                } else if (po.status === 'CLOSED') {
                    statusBadge = '<span class="bg-slate-200 text-slate-700 text-[10px] px-2 py-0.5 rounded-full font-bold">CLOSED</span>';
                }

                card.innerHTML = `
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-mono font-bold text-slate-900">${po.po_number}</span>
                        ${statusBadge}
                    </div>
                    <p class="text-xs font-bold text-slate-800 truncate mb-1">${po.vendor_name}</p>
                    <p class="text-[11px] text-slate-500 mb-3 line-clamp-1">${po.description}</p>
                    
                    <div class="space-y-1 mb-3">
                        <div class="flex items-center justify-between text-[11px] text-slate-500">
                            <span>Committed Spend:</span>
                            <span class="font-bold text-slate-800">$${invoiced.toLocaleString()} / $${total.toLocaleString()}</span>
                        </div>
                        <div class="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                            <div class="bg-sky-600 h-full rounded-full" style="width: ${pct}%"></div>
                        </div>
                    </div>

                    <div class="pt-2 border-t border-slate-200 flex items-center justify-between text-[11px]">
                        <span class="text-slate-500">Remaining Balance:</span>
                        <span class="font-bold font-mono text-emerald-700">$${remaining.toLocaleString()}</span>
                    </div>
                `;
                grid.appendChild(card);
            });
        });
}

function loadVendors() {
    fetch('/api/vendors')
        .then(r => r.json())
        .then(data => {
            const grid = document.getElementById('vendors-grid');
            grid.innerHTML = '';
            data.vendors.forEach(v => {
                const card = document.createElement('div');
                card.className = 'bg-slate-50 border border-slate-200 rounded-xl p-5 hover:border-slate-300 transition-all shadow-2xs';

                const bank = v.remittance_bank || {};

                card.innerHTML = `
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-mono text-xs font-bold text-sky-700">${v.id}</span>
                        <span class="bg-emerald-100 text-emerald-800 text-[10px] px-2 py-0.5 rounded-full font-bold">${v.status}</span>
                    </div>
                    <h4 class="text-sm font-bold text-slate-900 truncate mb-0.5">${v.name}</h4>
                    <p class="text-[11px] text-slate-500 font-mono mb-3">Tax ID: ${v.tax_id}</p>

                    <div class="bg-white p-3 rounded-lg border border-slate-200 text-xs space-y-1 mb-3 font-mono">
                        <span class="text-slate-400 block text-[10px] uppercase font-semibold">Approved Remittance</span>
                        <div class="text-slate-800 font-bold">${bank.bank_name || 'N/A'}</div>
                        <div class="text-slate-600">Routing: <span class="text-sky-700 font-bold">${bank.routing_number || 'N/A'}</span></div>
                        <div class="text-slate-600">Account: ${bank.account_display || 'N/A'}</div>
                    </div>

                    <div class="flex items-center justify-between text-[11px] text-slate-500">
                        <span>Tolerance Limit:</span>
                        <span class="font-semibold text-slate-800">${v.tolerance_percent}% (Max $${v.tolerance_amount_max})</span>
                    </div>
                `;
                grid.appendChild(card);
            });
        });
}

// -------------------------------------------------------------
// Reset Demo Baseline
// -------------------------------------------------------------
function resetDemoBaseline() {
    if (!confirm("Reset all PO balances and runs history to fresh demo state?")) return;

    fetch('/api/reset', { method: 'POST' })
        .then(r => r.json())
        .then(res => {
            alert(res.message);
            loadDashboardStats();
            loadRunsHistory('ALL');
            loadPOs();
            loadVendors();
            resetStepperUI();
        });
}

// -------------------------------------------------------------
// Audit Modal Drilldown
// -------------------------------------------------------------
function viewRunAuditModal(runId) {
    fetch(`/api/run/${runId}`)
        .then(r => r.json())
        .then(run => {
            const modal = document.getElementById('audit-modal');
            document.getElementById('modal-title').textContent = `Audit Trail: ${run.run_id}`;
            document.getElementById('modal-subtitle').textContent = `Invoice #${run.invoice_number || 'N/A'} · ${run.vendor_name || 'Unknown'} · Processed at ${run.timestamp}`;

            const body = document.getElementById('modal-body');
            body.innerHTML = `
                <!-- Top Summary Banner -->
                <div class="p-4 rounded-xl border ${run.status === 'APPROVED' ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : (run.status === 'NEEDS_REVIEW' ? 'bg-amber-50 border-amber-200 text-amber-900' : 'bg-rose-50 border-rose-200 text-rose-900')}">
                    <div class="flex items-center justify-between text-xs font-bold mb-1">
                        <span>FINAL VERDICT: ${run.status}</span>
                        <span>Confidence: ${Math.round(run.confidence_score * 100)}%</span>
                    </div>
                    <p class="text-xs leading-relaxed font-medium">${run.summary}</p>
                </div>

                <!-- Stage Latency Breakdown -->
                <div>
                    <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Stage Execution Trace</h4>
                    <div class="space-y-1.5">
                        ${(run.stage_logs || []).map(s => `
                            <div class="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                                <div class="flex items-center space-x-2">
                                    <span class="w-5 h-5 rounded-full ${s.status === 'COMPLETED' ? 'bg-emerald-500 text-white' : (s.status === 'WARNING' ? 'bg-amber-500 text-white' : 'bg-rose-500 text-white')} flex items-center justify-center text-[10px] font-bold">${s.stage_number}</span>
                                    <span class="font-bold text-slate-800">${s.stage_name}</span>
                                    <span class="text-slate-500 truncate max-w-sm">(${s.summary})</span>
                                </div>
                                <span class="font-mono text-slate-500 text-[11px]">${s.duration_ms}ms</span>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <!-- Rules Checklist -->
                <div>
                    <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Evaluated Rules Audit</h4>
                    <div class="space-y-1.5">
                        ${(run.rule_evaluations || []).map(r => `
                            <div class="p-2.5 rounded-lg border text-xs flex items-center justify-between ${r.status === 'PASS' ? 'bg-emerald-50/50 border-emerald-200 text-emerald-900' : (r.status === 'WARN' ? 'bg-amber-50/50 border-amber-200 text-amber-900' : 'bg-rose-50/50 border-rose-200 text-rose-900')}">
                                <div>
                                    <span class="font-bold">${r.rule_name}</span>: ${r.message}
                                </div>
                                <span class="font-bold text-[10px] px-2 py-0.5 rounded bg-white border border-slate-200">${r.status}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <!-- Stored Raw Extracted JSON -->
                <div>
                    <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Structured Extracted JSON Object</h4>
                    <pre class="bg-slate-900 text-slate-200 p-3 rounded-xl text-[11px] font-mono overflow-x-auto max-h-48 custom-scrollbar">${JSON.stringify(run.extracted_data, null, 2)}</pre>
                </div>
            `;

            modal.classList.remove('hidden');
        });
}

function closeAuditModal() {
    document.getElementById('audit-modal').classList.add('hidden');
}

