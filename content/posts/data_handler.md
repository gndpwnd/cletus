+++
author = "cletus"
title = "Data Analysis"
date = "2025-03-01"
description = "Merge JSON, Generate Markdown, Convert MD to PDF"
tags = [
    "Analysis",
]
+++

<h2>Upload JSON or Markdown Files</h2>
<input type="file" id="fileInput" multiple accept=".json,.md" onchange="displaySelectedFiles()">
<button onclick="mergeJSON()">Merge and Download JSON</button>
<button onclick="generateReport()">Generate Report (Markdown)</button>
<button onclick="convertToPDF()" id="pdf-button" disabled>Convert to PDF</button>

<div id="fileListContainer">
    <!-- Uploaded files list -->
</div>

<!-- Markdown output container (hidden until report is generated) -->
<div id="markdown-container" style="margin-top: 20px; display: none;">
    <h3>Generated Report</h3>
    <div style="position: relative;">
        <pre id="markdown-output" style="background: #f5f5f5; padding: 15px; border-radius: 5px; border: 1px solid #ddd; overflow-x: auto;"></pre>
        <button id="copy-button" style="position: absolute; top: 10px; right: 10px; background: #4CAF50; color: white; border: none; border-radius: 3px; padding: 5px 10px; cursor: pointer;">Copy</button>
    </div>
</div>

<!-- Load libraries -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>

<script>
    let fileContents = {};
    let selectedFiles = [];
    let mergedData = {};

    // --- Existing functions (unchanged) ---
    function displaySelectedFiles() { /* ... */ }
    function readFileContent(file) { /* ... */ }
    function updateFileList() { /* ... */ }
    function removeFile(index) { /* ... */ }
    function rebuildMergedData() { /* ... */ }
    function mergeJSON() { /* ... */ }
    function mergeData(newData) { /* ... */ }
    function downloadMergedJSON() { /* ... */ }

    // --- New/Modified Functions ---

    // Generate Markdown Report
    function generateReport() {
        if (Object.keys(mergedData).length === 0) {
            alert("No JSON data available. Merge files first.");
            return;
        }

        let markdown = `# News Report\n\n`;
        const date = Object.keys(mergedData)[0];
        markdown += `**Date:** ${date}\n\n`;
        markdown += `**Generated on:** ${new Date().toLocaleDateString()}\n\n`;
        markdown += `**Author:** Cletus\n\n---\n\n`;

        // Add data by category
        for (const category in mergedData[date]) {
            markdown += `## ${category}\n\n`;
            for (const articleId in mergedData[date][category]) {
                const article = mergedData[date][category][articleId];
                markdown += `### ${article.headline}\n\n`;
                markdown += `- [Link](${article.link})\n`;
                markdown += `- [Search](${article.search})\n\n`;
                markdown += `**Analysis:**\n\nLorem ipsum...\n\n---\n\n`;
            }
        }

        // Display in code block
        const output = document.getElementById("markdown-output");
        output.textContent = markdown;
        document.getElementById("markdown-container").style.display = "block";
        document.getElementById("pdf-button").disabled = false;

        // Copy button logic
        document.getElementById("copy-button").onclick = () => {
            navigator.clipboard.writeText(markdown)
                .then(() => alert("Copied to clipboard!"))
                .catch(err => console.error("Failed to copy:", err));
        };
    }

    // Convert Markdown to PDF
    async function convertToPDF() {
        const markdownFiles = selectedFiles.filter(file => file.name.endsWith('.md'));
        const generatedMarkdown = document.getElementById("markdown-output")?.textContent.trim();

        // Case 1: No Markdown content found
        if (markdownFiles.length === 0 && !generatedMarkdown) {
            alert("No Markdown content found. Generate a report or upload .md files.");
            return;
        }

        // Case 2: Process uploaded .md files
        if (markdownFiles.length > 0) {
            for (const file of markdownFiles) {
                const markdown = await readFileAsText(file);
                const pdfName = file.name.replace('.md', '.pdf');
                await generatePDFFromMarkdown(markdown, pdfName);
            }
        }

        // Case 3: Process generated Markdown (if exists)
        if (generatedMarkdown) {
            await generatePDFFromMarkdown(generatedMarkdown, "cletus_report.pdf");
        }
    }

    // Helper: Read file as text
    function readFileAsText(file) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.readAsText(file);
        });
    }

    // Helper: Convert Markdown to PDF and download
    function generatePDFFromMarkdown(markdown, filename) {
        return new Promise((resolve) => {
            const html = marked.parse(markdown);
            const element = document.createElement("div");
            element.innerHTML = html;
            document.body.appendChild(element);

            // Add basic styling
            const style = document.createElement("style");
            style.textContent = `
                body { font-family: Arial; line-height: 1.6; padding: 20px; }
                h1 { color: #333; border-bottom: 1px solid #eee; }
                pre { background: #f5f5f5; padding: 10px; }
            `;
            element.appendChild(style);

            // Generate PDF
            html2pdf()
                .from(element)
                .set({ 
                    filename,
                    margin: 10,
                    html2canvas: { scale: 2 },
                    jsPDF: { unit: "mm", format: "a4" }
                })
                .save()
                .then(() => {
                    document.body.removeChild(element);
                    resolve();
                });
        });
    }
</script>