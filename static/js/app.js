document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('process-btn');
    const input = document.getElementById('raw-signal');
    const spinner = document.getElementById('spinner');
    const errorMsg = document.getElementById('error-msg');
    
    const placeholder = document.getElementById('output-placeholder');
    const results = document.getElementById('results');
    
    // UI Elements
    const priorityBadge = document.getElementById('priority-badge');
    const severityText = document.getElementById('res-severity');
    const intentText = document.getElementById('res-intent');
    const locationText = document.getElementById('res-location');
    const actionText = document.getElementById('res-action');
    const jsonCode = document.getElementById('json-code');

    btn.addEventListener('click', async () => {
        const text = input.value.trim();
        if (!text) return;

        // UI Loading State
        btn.disabled = true;
        spinner.classList.remove('hidden');
        errorMsg.classList.add('hidden');
        placeholder.classList.add('hidden');
        results.classList.add('hidden');

        try {
            const response = await fetch('/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to process signal.');
            }

            // Populate UI
            priorityBadge.textContent = `Priority ${data.priority_level}`;
            priorityBadge.className = `badge priority-${data.priority_level}`;
            
            severityText.textContent = data.severity;
            intentText.textContent = data.intent;
            locationText.textContent = data.location_summary;
            actionText.textContent = data.actionable_recommendation;
            
            jsonCode.textContent = JSON.stringify(data, null, 2);

            results.classList.remove('hidden');

        } catch (err) {
            errorMsg.textContent = err.message || "An unexpected error occurred.";
            errorMsg.classList.remove('hidden');
            placeholder.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            spinner.classList.add('hidden');
        }
    });
});
