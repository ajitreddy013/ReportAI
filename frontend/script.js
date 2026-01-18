document.getElementById('reportForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);
    const statusEl = document.getElementById('status');
    const generateBtn = document.getElementById('generateBtn');

    // Show loading status
    statusEl.textContent = 'Generating your report... Please wait.';
    statusEl.classList.remove('hidden', 'error', 'success');
    statusEl.classList.add('loading');
    generateBtn.disabled = true;

    try {
        const response = await fetch('http://localhost:8000/generate-report', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to generate report');
        }

        // Handle file download
        const blob = await response.blob();
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'Report.docx';
        
        if (contentDisposition && contentDisposition.includes('filename=')) {
            filename = contentDisposition.split('filename=')[1].split(';')[0].replace(/"/g, '');
        }

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        statusEl.textContent = 'Report generated and downloaded successfully!';
        statusEl.classList.replace('loading', 'success');

    } catch (error) {
        console.error('Error:', error);
        statusEl.textContent = `Error: ${error.message}`;
        statusEl.classList.replace('loading', 'error');
    } finally {
        generateBtn.disabled = false;
    }
});
