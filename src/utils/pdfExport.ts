import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

export const exportToPDF = async (elementId: string, fileName: string = 'dashboard') => {
    try {
        const element = document.getElementById(elementId);
        if (!element) {
            throw new Error('Element not found');
        }

        // Show loading state
        const originalCursor = document.body.style.cursor;
        document.body.style.cursor = 'wait';

        // Wait for charts to render completely
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Create canvas from the element
        const canvas = await html2canvas(element, {
            scale: 1.5, // Good balance between quality and file size
            useCORS: true,
            allowTaint: true,
            backgroundColor: '#0f172a', // Dark background to match theme
            removeContainer: false,
            scrollX: 0,
            scrollY: 0,
            width: element.scrollWidth,
            height: element.scrollHeight,
            onclone: (clonedDoc) => {
                // Ensure all SVG elements are visible in the cloned document
                const clonedElement = clonedDoc.getElementById(elementId);
                if (clonedElement) {
                    // Force visibility of all SVG elements
                    const svgElements = clonedElement.querySelectorAll('svg');
                    svgElements.forEach(svg => {
                        svg.style.display = 'block';
                        svg.style.visibility = 'visible';
                    });

                    // Ensure charts container is properly sized
                    const chartContainers = clonedElement.querySelectorAll('.recharts-wrapper');
                    chartContainers.forEach(container => {
                        (container as HTMLElement).style.width = '100%';
                        (container as HTMLElement).style.height = 'auto';
                    });
                }
            }
        });

        // Calculate PDF dimensions (A4 landscape for better dashboard viewing)
        const pdf = new jsPDF('l', 'mm', 'a4'); // landscape orientation
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = pdf.internal.pageSize.getHeight();

        const imgWidth = pdfWidth;
        const imgHeight = (canvas.height * imgWidth) / canvas.width;

        let heightLeft = imgHeight;
        let position = 0;

        // Add the first page
        pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pdfHeight;

        // Add additional pages if needed
        while (heightLeft >= 0) {
            position = heightLeft - imgHeight;
            pdf.addPage();
            pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, position, imgWidth, imgHeight);
            heightLeft -= pdfHeight;
        }

        // Save the PDF
        const timestamp = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().split('T')[0];
        pdf.save(`${fileName}_${timestamp}.pdf`);

        // Restore cursor
        document.body.style.cursor = originalCursor;

        return { success: true, message: 'PDF exported successfully' };
    } catch (error) {
        console.error('Error exporting PDF:', error);
        document.body.style.cursor = 'default';
        throw new Error('Failed to export PDF');
    }
};

export const exportDashboardToPDF = async (dashboardTitle: string) => {
    const fileName = dashboardTitle.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_').toLowerCase() || 'dashboard';
    return exportToPDF('dashboard-content', fileName);
};
