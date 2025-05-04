document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    let fileContents = {};
    let selectedFiles = [];
    let mergedData = {};
    
    // Get DOM elements
    const fileInput = document.getElementById('fileInput');
    const mergeButton = document.getElementById('mergeButton');
    const reportButton = document.getElementById('reportButton');
    const markdownContainer = document.getElementById('markdown-container');
    const markdownOutput = document.getElementById('markdown-output');
    const copyButton = document.getElementById('copy-button');
    const downloadButton = document.getElementById('download-button');
    const pdfButton = document.getElementById('pdf-button');
    const fileListContainer = document.getElementById('fileListContainer');
    
    // Set up event listeners
    fileInput.addEventListener('change', handleFileSelection);
    mergeButton.addEventListener('click', mergeJSON);
    reportButton.addEventListener('click', generateReport);
    copyButton.addEventListener('click', copyToClipboard);
    downloadButton.addEventListener('click', () => {
        if (markdownOutput.textContent.trim()) {
            downloadMarkdown(markdownOutput.textContent);
        } else {
            alert('No markdown content to download. Generate a report first.');
        }
    });
    pdfButton.addEventListener('click', () => {
        if (markdownOutput.textContent.trim()) {
            generatePDFFromMarkdown(markdownOutput.textContent, "cletus_report.pdf");
        } else {
            alert('No markdown content to convert. Generate a report first.');
        }
    });
    
    // --- Functions ---
    function handleFileSelection() {
        const newFiles = Array.from(fileInput.files);
        
        // Check for duplicates and only add new files
        newFiles.forEach(newFile => {
            const isDuplicate = selectedFiles.some(
                existingFile => existingFile.name === newFile.name && 
                              existingFile.size === newFile.size &&
                              existingFile.lastModified === newFile.lastModified
            );
            
            if (!isDuplicate) {
                selectedFiles.push(newFile);
            }
        });
        
        updateFileList();
        fileInput.value = ''; // Clear the input to allow selecting same files again
    }
    
    function updateFileList() {
        fileListContainer.innerHTML = '<h3>Selected Files</h3>';
        
        if (selectedFiles.length === 0) {
            fileListContainer.innerHTML += '<p>No files selected</p>';
            return;
        }
        
        const list = document.createElement('ul');
        selectedFiles.forEach((file, index) => {
            const item = document.createElement('li');
            item.innerHTML = `
                <span>${file.name} (${formatFileSize(file.size)})</span>
                <button data-index="${index}" class="remove-btn">✕</button>
            `;
            list.appendChild(item);
        });
        fileListContainer.appendChild(list);
        
        // Add remove event listeners
        fileListContainer.querySelectorAll('.remove-btn').forEach(button => {
            button.addEventListener('click', function() {
                const index = parseInt(this.getAttribute('data-index'));
                selectedFiles.splice(index, 1);
                updateFileList();
            });
        });
    }
    
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' bytes';
        else if (bytes < 1048576) return (bytes / 1024).toFixed(2) + ' KB';
        else return (bytes / 1048576).toFixed(2) + ' MB';
    }
    
    async function readFileContent(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(e);
            reader.readAsText(file);
        });
    }
    
    async function mergeJSON() {
        if (selectedFiles.length === 0) {
            alert("No files selected");
            return;
        }

        mergedData = {};
        let jsonFilesFound = false;
        
        for (const file of selectedFiles) {
            try {
                const content = await readFileContent(file);
                if (file.name.endsWith('.json')) {
                    jsonFilesFound = true;
                    const jsonData = JSON.parse(content);
                    mergeData(jsonData);
                }
            } catch (error) {
                console.error(`Error processing ${file.name}:`, error);
                alert(`Error processing ${file.name}: ${error.message}`);
            }
        }

        if (Object.keys(mergedData).length > 0) {
            downloadMergedJSON();
        } else if (jsonFilesFound) {
            alert("No valid JSON data found in selected files");
        } else {
            alert("No JSON files selected");
        }
    }
    
    function mergeData(newData) {
        for (const date in newData) {
            if (!mergedData[date]) {
                mergedData[date] = {};
            }
            
            for (const category in newData[date]) {
                if (!mergedData[date][category]) {
                    mergedData[date][category] = {};
                }
                
                Object.assign(mergedData[date][category], newData[date][category]);
            }
        }
    }
    
    function downloadMergedJSON() {
        const blob = new Blob([JSON.stringify(mergedData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'merged_data.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    async function generateReport() {
        // First check if we have mergedData from previous merge operation
        if (Object.keys(mergedData).length === 0) {
            // If not, look for any merged_data*.json in selected files
            const mergedFiles = selectedFiles.filter(file => 
                file.name.toLowerCase().startsWith('merged_data') && 
                file.name.toLowerCase().endsWith('.json')
            );
            
            if (mergedFiles.length === 0) {
                alert('No merged data found. Please upload a "merged_data*.json" file or merge files first.');
                return;
            }
            
            // Use the first matching file
            try {
                const content = await readFileContent(mergedFiles[0]);
                mergedData = JSON.parse(content);
            } catch (error) {
                console.error('Error parsing merged data file:', error);
                alert('Error parsing merged data file. Please check the file and try again.');
                return;
            }
        }
    
        // Get current date in YYYY-MM-DD format
        const currentDate = new Date().toISOString().split('T')[0];
        
        // Generate consistent markdown report
        let markdown = `# Cletus News Report\n\n`;
        markdown += `**Date:** ${currentDate}\n\n`;
        markdown += `**Author:** Cletus\n\n`;
        markdown += `---\n\n`;
    
        const date = Object.keys(mergedData)[0];
        for (const category in mergedData[date]) {
            markdown += `## ${category}\n\n`;
            markdown += `---\n\n`;  // Add separator after category title
            
            for (const articleId in mergedData[date][category]) {
                const article = mergedData[date][category][articleId];
                markdown += `### ${article.headline}\n\n`;
                markdown += `- [Link](${article.link})\n`;
                markdown += `- [Search](${article.search})\n\n`;
                markdown += `**Analysis:**\n\nLorem ipsum...\n\n`;
                markdown += `---\n\n`;  // Add separator between articles
            }
        }
    
        // Update UI
        markdownOutput.textContent = markdown;
        markdownContainer.style.display = "block";
    }
    
    function downloadMarkdown(markdownContent) {
        const blob = new Blob([markdownContent], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'cletus_report.md';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    function copyToClipboard() {
        const markdown = markdownOutput.textContent;
        navigator.clipboard.writeText(markdown)
            .then(() => alert("Copied to clipboard!"))
            .catch(err => {
                console.error("Failed to copy:", err);
                alert("Failed to copy to clipboard");
            });
    }
    
    function generatePDFFromMarkdown(markdown, filename) {
        return new Promise((resolve, reject) => {
            try {
                const html = marked.parse(markdown);
                const element = document.createElement("div");
                element.innerHTML = html;
                document.body.appendChild(element);

                const style = document.createElement("style");
                style.textContent = `
                    .title-page {
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        text-align: center;
                        page-break-after: always;
                    }
                    .report-title {
                        font-size: 2.5rem;
                        color: #2c3e50;
                        margin-bottom: 20px;
                    }
                    .category-section {
                        page-break-before: always;
                        padding-top: 20px;
                    }
                    .category-title {
                        font-size: 1.8rem;
                        color: #3498db;
                        margin-bottom: 30px;
                        border-bottom: 2px solid #3498db;
                        padding-bottom: 10px;
                    }
                    .article {
                        margin-bottom: 20px;
                    }
                    body { 
                        font-family: Arial; 
                        line-height: 1.6; 
                        padding: 20px; 
                    }
                    pre { 
                        background: #f5f5f5; 
                        padding: 15px; 
                        border-radius: 5px;
                    }
                    a { 
                        color: #3498db; 
                        text-decoration: none;
                    }
                `;
                element.appendChild(style);

                const options = {
                    filename: filename,
                    margin: 15,
                    image: { type: 'jpeg', quality: 0.98 },
                    html2canvas: { 
                        scale: 2,
                        logging: false,
                        useCORS: true
                    },
                    jsPDF: { 
                        unit: 'mm', 
                        format: 'a4', 
                        orientation: 'portrait'
                    }
                };

                html2pdf()
                    .set(options)
                    .from(element)
                    .save()
                    .then(() => {
                        document.body.removeChild(element);
                        resolve();
                    })
                    .catch(error => {
                        document.body.removeChild(element);
                        reject(error);
                    });
            } catch (error) {
                reject(error);
            }
        });
    }
});