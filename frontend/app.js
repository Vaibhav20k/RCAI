// Investigation Console Client Application
const API_BASE = "http://localhost:8000";

let currentIncidentId = null;

async function loadIncidents() {
    try {
        const resp = await fetch(`${API_BASE}/api/incidents`);
        const incidents = await resp.json();
        const container = document.getElementById("incidents-list");
        if (!incidents || incidents.length === 0) {
            container.innerHTML = "<p>No active incidents.</p>";
            return;
        }
        currentIncidentId = incidents[0].incident_id;
        container.innerHTML = incidents.map(inc => `
            <div class="incident-item">
                <strong>[${inc.severity}] ${inc.service}</strong>: ${inc.symptom}
                <div class="incident-meta">Status: <code>${inc.status}</code> | ID: <code>${inc.incident_id}</code></div>
            </div>
        `).join("");
    } catch (e) {
        document.getElementById("incidents-list").innerHTML = "<p>Failed to connect to API backend.</p>";
    }
}

document.getElementById("btn-start-investigation").addEventListener("click", async () => {
    if (!currentIncidentId) return;
    const btn = document.getElementById("btn-start-investigation");
    btn.disabled = true;
    btn.innerText = "Investigating...";

    try {
        const resp = await fetch(`${API_BASE}/api/investigate/${currentIncidentId}`, { method: "POST" });
        const data = await resp.json();
        
        // Render Hypotheses
        const topH = data.top_hypothesis;
        document.getElementById("hypothesis-list").innerHTML = `
            <div class="hypothesis-item confirmed">
                <strong>Diagnosis:</strong> ${topH.description}<br>
                <strong>Confidence:</strong> ${(topH.confidence * 100).toFixed(1)}%<br>
                <strong>Status:</strong> ${topH.status}
            </div>
        `;

        // Render Action Timeline
        document.getElementById("action-timeline").innerHTML = data.action_history.map(a => `
            <div class="action-item">
                Step ${a.step_index}: <code>${a.tool_name}</code> (${a.duration_ms.toFixed(1)}ms) -> ${a.result_status}
            </div>
        `).join("");

        // Render Evidence
        document.getElementById("evidence-trail").innerHTML = data.report.evidence_trail.map(ev => `
            <div class="evidence-item">
                <strong>[${ev.source}]</strong> ${ev.summary}<br>
                <code>Collector: ${ev.collector} | Hash: ${ev.hash_signature.slice(0, 16)}...</code>
            </div>
        `).join("");

        // Show Remediation Option
        document.getElementById("remediation-actions").classList.remove("hidden");
        document.getElementById("remediation-prompt").innerText = `Recommended: ${data.report.recommended_action}`;

    } catch (e) {
        alert("Investigation error: " + e);
    } finally {
        btn.disabled = false;
        btn.innerText = "Run Autonomous Investigation";
    }
});

loadIncidents();
