+++
author = "cletus"
title = "Analysis - JSON Merger"
date = "2025-03-01"
description = "Merge JSON Files"
tags = [
    "Analysis",
]
+++

<h2>Upload JSON Files</h2>
<input type="file" id="fileInput" multiple accept=".json" onchange="displaySelectedFiles()">
<button onclick="mergeJSON()">Merge and Download</button>
<button onclick="generatePDF()">Generate PDF</button>

<div id="fileListContainer">
    <!-- List of uploaded files will appear here -->
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.28/jspdf.plugin.autotable.min.js"></script>

<script>
    let fileContents = {}; // Store file contents by name
    let selectedFiles = [];
    let mergedData = {};

    function displaySelectedFiles() {
        const fileInput = document.getElementById('fileInput');
        const fileListContainer = document.getElementById('fileListContainer');
        
        // Add each file to the selectedFiles array if not already there
        for (let file of fileInput.files) {
            if (!selectedFiles.some(f => f.name === file.name)) {
                selectedFiles.push(file);
                // Read the file content immediately but don't merge yet
                readFileContent(file);
            }
        }

        // Display the list of selected files
        updateFileList();
        
        // Clear the file input to allow selecting the same file again if needed
        fileInput.value = '';
    }
    
    function readFileContent(file) {
        let reader = new FileReader();
        reader.onload = (event) => {
            try {
                let jsonData = JSON.parse(event.target.result);
                // Store the parsed content by filename
                fileContents[file.name] = jsonData;
                console.log(`File content stored: ${file.name}`);
            } catch (error) {
                console.error(`Error parsing ${file.name}: ${error.message}`);
                alert(`Error parsing ${file.name}: ${error.message}`);
                // Remove the file if it can't be parsed
                removeFile(selectedFiles.findIndex(f => f.name === file.name));
            }
        };
        reader.onerror = () => {
            console.error(`Error reading ${file.name}`);
            alert(`Error reading ${file.name}`);
            // Remove the file if it can't be read
            removeFile(selectedFiles.findIndex(f => f.name === file.name));
        };
        reader.readAsText(file);
    }

    function updateFileList() {
        const fileListContainer = document.getElementById('fileListContainer');
        fileListContainer.innerHTML = '';  // Clear the existing list
        
        // Display the list of selected files
        selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.classList.add('file-item');
            fileItem.style.margin = '10px 0';
            fileItem.style.padding = '5px';
            fileItem.style.border = '1px solid #ccc';
            fileItem.style.borderRadius = '5px';
            fileItem.style.display = 'flex';
            fileItem.style.justifyContent = 'space-between';

            const fileName = document.createElement('span');
            fileName.textContent = file.name;
            fileName.style.padding = '5px';

            const deleteButton = document.createElement('button');
            deleteButton.textContent = 'Remove';
            deleteButton.style.backgroundColor = '#ff4d4d';
            deleteButton.style.color = 'white';
            deleteButton.style.border = 'none';
            deleteButton.style.borderRadius = '3px';
            deleteButton.style.padding = '5px 10px';
            deleteButton.style.cursor = 'pointer';
            deleteButton.onclick = () => removeFile(index);

            fileItem.appendChild(fileName);
            fileItem.appendChild(deleteButton);

            fileListContainer.appendChild(fileItem);
        });
    }

    function removeFile(index) {
        if (index < 0 || index >= selectedFiles.length) return;
        
        // Get the name of the file being removed
        let removedFileName = selectedFiles[index].name;
        
        // Remove the file from the selectedFiles array
        selectedFiles.splice(index, 1);
        
        // Remove the file content from our fileContents object
        delete fileContents[removedFileName];
        
        console.log(`File removed: ${removedFileName}`);
        
        // Re-render the file list after removal
        updateFileList();
        
        // Reset mergedData and rebuild it from the remaining files
        rebuildMergedData();
    }
    
    function rebuildMergedData() {
        // Reset merged data
        mergedData = {};
        
        // Rebuild from the current file contents
        for (let fileName in fileContents) {
            mergeData(fileContents[fileName]);
        }
        
        console.log("Merged data rebuilt after file removal");
    }

    function mergeJSON() {
        if (selectedFiles.length === 0) {
            alert("Please upload at least one JSON file.");
            return;
        }

        // Reset merged data before merging
        mergedData = {};
        
        // Use the stored file contents to merge
        for (let fileName in fileContents) {
            mergeData(fileContents[fileName]);
        }
        
        downloadMergedJSON();
    }

    function mergeData(newData) {
        for (let date in newData) {
            if (!mergedData[date]) {
                mergedData[date] = {};
            }

            for (let category in newData[date]) {
                if (!mergedData[date][category]) {
                    mergedData[date][category] = {};
                }

                for (let articleId in newData[date][category]) {
                    mergedData[date][category][articleId] = newData[date][category][articleId];
                }
            }
        }
    }

    function downloadMergedJSON() {
        if (Object.keys(mergedData).length === 0) {
            alert("No data to merge. Please check your JSON files.");
            return;
        }
        
        let jsonString = JSON.stringify(mergedData, null, 4);
        let blob = new Blob([jsonString], { type: 'application/json' });
        let link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `merged_articles.json`;
        link.click();
    }

	async function generatePDF() {
	    // First ensure we have the latest merged data
	    if (selectedFiles.length === 0) {
	        alert("Please upload at least one JSON file.");
	        return;
	    }
	    
	    // Reset and rebuild merged data to ensure it's current
	    mergedData = {};
	    for (let fileName in fileContents) {
	        mergeData(fileContents[fileName]);
	    }
	    
	    if (Object.keys(mergedData).length === 0) {
	        alert("No valid data available. Upload JSON files with proper structure.");
	        return;
	    }

	    // Create a new jsPDF instance (using points as unit)
	    const doc = new jspdf.jsPDF({
	        unit: 'pt',
	        format: 'letter'
	    });
	    
	    // Set margins in points (72 points = 1 inch)
	    const sideMargin = 72; // 1 inch side margins
	    const bottomMargin = 72; // 1 inch bottom margin
	    const firstPageTopMargin = 144; // 2 inches from top on first page
	    const succeedingPagesTopMargin = 72; // 1 inch from top on succeeding pages
	    
	    // Title page spacing constants
	    const titleToCreatedSpacing = 30; // Space between "News Report" and "Created on"
	    const createdToReportDateSpacing = 25; // Space between "Created on" and "Report Date"
	    const reportDateToAuthorSpacing = 25; // Space between "Report Date" and "Author"
	    
	    // Content spacing constants - using your provided values
	    const headlineToLinksSpacing = 15; // Space between headline and links
	    const linksToAnalysisSpacing = 20; // Space between links and analysis heading
	    const analysisHeadingToTextSpacing = 20; // Space between "Analysis:" and the text
	    const analysisToSourcesSpacing = 10; // Space between analysis text and sources
	    const sourcesHeadingToListSpacing = 15; // Space between "Analysis Sources:" and the first source
	    const betweenSourcesSpacing = 5; // Space between sources
	    const afterArticleSpacing = 40; // Space after each article
	    
	    // Get page dimensions
	    const pageWidth = doc.internal.pageSize.getWidth();
	    const pageHeight = doc.internal.pageSize.getHeight();
	    const textWidth = pageWidth - (sideMargin * 2);
	    
	    // Get the date from the data
	    let date = Object.keys(mergedData)[0];
	    
	    // Title page content with improved spacing
	    doc.setFontSize(24);
	    doc.setFont("times", "bold");
	    doc.text("News Report", pageWidth / 2, firstPageTopMargin, { align: "center" });

	    // Add spacing after title
	    doc.setFontSize(16);
	    doc.setFont("times", "normal");
	    doc.text("Created on " + new Date().toLocaleDateString(), pageWidth / 2, firstPageTopMargin + titleToCreatedSpacing, { align: "center" });
	    
	    // Add spacing after "Created on"
	    doc.setFontSize(16);
	    doc.text("Report Date: " + date, pageWidth / 2, firstPageTopMargin + titleToCreatedSpacing + createdToReportDateSpacing, { align: "center" });
	    
	    // Add spacing after "Report Date"
	    doc.setFontSize(14);
	    doc.text("Author: Cletus", pageWidth / 2, firstPageTopMargin + titleToCreatedSpacing + createdToReportDateSpacing + reportDateToAuthorSpacing, { align: "center" });

	    // Function to check if we need a new page
	    function checkForNewPage(currentY, requiredSpace) {
	        if (currentY + requiredSpace > pageHeight - bottomMargin) {
	            doc.addPage();
	            return succeedingPagesTopMargin; // Reset y position to top margin of succeeding pages
	        }
	        return currentY;
	    }

	    // Process each category in the data
	    for (let category in mergedData[date]) {
	        // Add a new page for each category
	        doc.addPage();
	        let y = succeedingPagesTopMargin; // Start position for content on succeeding pages

	        // Draw category name in 20pt font
	        doc.setFontSize(20);
	        doc.setFont("times", "bold");
	        const safeCategory = sanitizeText(category);
	        doc.text(safeCategory, sideMargin, y);
	        y += 30; // Increased spacing after category heading

	        // Process each article in the category
	        for (let articleId in mergedData[date][category]) {
	            let article = mergedData[date][category][articleId];
	            
	            // Check if we have enough space for at least the headline
	            y = checkForNewPage(y, 40); // Increased required space for headline

	            // Headline in bold
	            doc.setFontSize(12);
	            doc.setFont("times", "bold");
	            const safeHeadline = sanitizeText(article.headline);
	            const headlineLines = doc.splitTextToSize(safeHeadline, textWidth);
	            doc.text(headlineLines, sideMargin, y);
	            
	            // Calculate headline height and advance Y position
	            const headlineHeight = headlineLines.length * 15; // Increased line height for headline
	            y += headlineHeight;
	            
	            // Add spacing between headline and links
	            y += headlineToLinksSpacing;
	            
	            // Check if we have enough space for links
	            y = checkForNewPage(y, 20);

	            // Simple "link" text with hyperlink
	            doc.setFontSize(10);
	            doc.setFont("times", "normal");
	            
	            // Draw "link" text in blue and make it clickable
	            doc.setTextColor(0, 0, 255); // Blue color for links
	            doc.text("link", sideMargin, y);
	            
	            // Add hyperlink for the "link" text that opens in new tab
	            doc.link(sideMargin, y - 10, 15, 12, { url: article.link, newWindow: true });
	            
	            // Move to next position (horizontally)
	            const linkTextWidth = doc.getTextWidth("link");
	            const spaceBetween = 20; // Increased spacing between links
	            
	            // Draw "search" text and make it clickable
	            doc.text("search", sideMargin + linkTextWidth + spaceBetween, y);
	            
	            // Add hyperlink for the "search" text that opens in new tab
	            doc.link(sideMargin + linkTextWidth + spaceBetween, y - 10, 25, 12, { url: article.search, newWindow: true });
	            
	            // Add spacing between links and analysis
	            y += linksToAnalysisSpacing;
	            
	            // Check if we have enough space for analysis heading + first line
	            y = checkForNewPage(y, 30);

	            // Reset text color for analysis
	            doc.setTextColor(0, 0, 0); // Black text
	            
	            // Analysis heading
	            doc.setFontSize(12);
	            doc.setFont("times", "bold");
	            doc.text("Analysis:", sideMargin, y);
	            y += analysisHeadingToTextSpacing;

	            // Analysis text with indent
	            doc.setFontSize(10);
	            doc.setFont("times", "normal");
	            const analysisText = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.";
	            const safeAnalysis = sanitizeText(analysisText);
	            
	            // Wrap analysis text
	            const analysisLines = doc.splitTextToSize(safeAnalysis, textWidth - 10); // Account for indentation
	            
	            // Check if we need a new page for the analysis text
	            const analysisHeight = analysisLines.length * 14; // Increased line height for analysis
	            y = checkForNewPage(y, analysisHeight);
	            
	            doc.text(analysisLines, sideMargin + 10, y); // Indent by 10
	            y += analysisHeight;
	            
	            // Add spacing between analysis and sources
	            y += analysisToSourcesSpacing;
	            
	            // Check if we have enough space for source heading + first source
	            y = checkForNewPage(y, 30);
	            
	            // Add "Analysis Sources" section with bullet points
	            doc.setFontSize(10);
	            doc.setFont("times", "italic");
	            doc.text("Analysis Sources:", sideMargin, y);
	            y += sourcesHeadingToListSpacing;
	            
	            // Add bullet points for link and search
	            const bulletIndent = 15; // Increased bullet indent
	            
	            // Link bullet
	            const safeLinkUrl = sanitizeText(article.link);
	            const linkSourceLines = doc.splitTextToSize("• " + safeLinkUrl, textWidth - bulletIndent);
	            
	            // Check if we need a new page for the link source
	            const linkSourceHeight = linkSourceLines.length * 14; // Increased line height for sources
	            y = checkForNewPage(y, linkSourceHeight);
	            
	            doc.text(linkSourceLines, sideMargin + bulletIndent, y);
	            y += linkSourceHeight + betweenSourcesSpacing; // Added spacing between sources
	            
	            // Check if we need a new page for the search source
	            const safeSearchUrl = sanitizeText(article.search);
	            const searchSourceLines = doc.splitTextToSize("• " + safeSearchUrl, textWidth - bulletIndent);
	            const searchSourceHeight = searchSourceLines.length * 14; // Increased line height for sources
	            
	            y = checkForNewPage(y, searchSourceHeight);
	            
	            // Search bullet
	            doc.text(searchSourceLines, sideMargin + bulletIndent, y);
	            y += searchSourceHeight;
	            
	            // Extra space after article
	            y += afterArticleSpacing;
	        }
	    }

	    // Save and download the PDF
	    doc.save(`News_Report_${date}.pdf`);
	}

	// Function to sanitize text for PDF generation
	function sanitizeText(text) {
	    if (!text) return '';
	    
	    // Replace problematic characters with their closest ASCII equivalents
	    return text
	        .replace(/[\u2018\u2019]/g, "'") // Smart single quotes
	        .replace(/[\u201C\u201D]/g, '"') // Smart double quotes
	        .replace(/[\u2013\u2014]/g, '-') // En and em dashes
	        .replace(/[\u2026]/g, '...') // Ellipsis
	        .replace(/[\u00A0]/g, ' ') // Non-breaking space
	        .replace(/[\u00AD]/g, '-') // Soft hyphen
	        .replace(/[^\x00-\x7F]/g, '') // Remove any other non-ASCII characters
	        .trim();
	}
</script>