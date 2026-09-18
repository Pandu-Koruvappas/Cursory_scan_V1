import os
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

class ReportService:
    @staticmethod
    def generate_traceability_report(project_data: dict, audit_logs: list):
        """
        Generates a professional PDF Traceability & Governance Report.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle(
            'TitleStyle', parent=styles['Heading1'], fontSize=24, spaceAfter=20, textColor=colors.HexColor("#00f3ff")
        )
        sub_style = ParagraphStyle(
            'SubStyle', parent=styles['Normal'], fontSize=10, textColor=colors.grey, spaceAfter=30
        )
        
        elements = []
        
        # 1. Header
        elements.append(Paragraph("Requify Enterprise Traceability Report", title_style))
        elements.append(Paragraph(f"Project ID: {project_data.get('document_id')} | LOB: {project_data.get('lob')}", styles['Normal']))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", sub_style))
        elements.append(Spacer(1, 12))
        
        # 2. Executive Summary (from TRD/Extraction)
        elements.append(Paragraph("Project Governance Overview", styles['Heading2']))
        elements.append(Paragraph("This document provides an end-to-end audit trail from source requirements to engineering work items, including agentic reasoning and consensus logs.", styles['Normal']))
        elements.append(Spacer(1, 24))
        
        # 3. Traceability Matrix Table
        elements.append(Paragraph("Requirement Traceability Matrix", styles['Heading3']))
        
        data = [["Req ID", "Requirement Description", "Linked ADO Story", "Compliance Status"]]
        for fr in project_data.get("matrix", []):
            linked = ", ".join([l.get("id", "") for l in fr.get("links", [])]) or "NONE"
            status = "MAPPED" if fr.get("links") else "UNMAPPED RISK"
            data.append([fr.get("source_id"), (fr.get("source_desc")[:60] + '...') if len(fr.get("source_desc", "")) > 60 else fr.get("source_desc"), linked, status])
            
        t = Table(data, colWidths=[60, 240, 100, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a1a1a")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(t)
        elements.append(PageBreak())
        
        # 4. Audit Trail (Agent Reasoning)
        elements.append(Paragraph("Agentic Reasoning & Audit Log", styles['Heading2']))
        elements.append(Paragraph("Below is the immutable log of all specialized agent decisions during the analysis phase.", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        for log in audit_logs:
            elements.append(Paragraph(f"<b>{log.timestamp.strftime('%H:%M:%S')} - {log.agent_name}</b>: {log.action}", styles['Normal']))
            elements.append(Paragraph(f"<i>Reasoning:</i> {log.reasoning}", styles['Normal']))
            elements.append(Spacer(1, 8))
            
        doc.build(elements)
        buffer.seek(0)
        return buffer
