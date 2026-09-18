import aiohttp
import aiofiles
import aiofiles.os
import aiofiles.tempfile
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import ChannelAccount

from agents.knowledge_agent import KnowledgeAgent
from services.orchestrator import orchestrator
from models.models import ProjectStateModel

class BATeamsBot(ActivityHandler):
    def __init__(self):
        self.knowledge_agent = KnowledgeAgent()
        print("--- [SUCCESS] Microsoft Teams Bot Initialized ---")

    async def on_members_added_activity(
        self, members_added: list[ChannelAccount], turn_context: TurnContext
    ):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                welcome_text = (
                    "Welcome to BA Agent Pro on Teams! \n\n"
                    "You can ask me questions about P&C Insurance Guidelines, or attach a `.pdf` / `.docx` requirement document, and I'll generate a Gap Analysis and TRD for you instantly."
                )
                await turn_context.send_activity(MessageFactory.text(welcome_text))

    async def on_message_activity(self, turn_context: TurnContext):
        activity = turn_context.activity
        
        # Handle Attachments (BRD Ingestion)
        if activity.attachments and len(activity.attachments) > 0:
            await turn_context.send_activity(MessageFactory.text("I received your document. Initializing Discovery Swarm and analyzing requirements... "))
            
            attachment = activity.attachments[0]
            download_url = attachment.content_url
            file_name = attachment.name or "Teams_Document.pdf"
            temp_path = None
            
            try:
                # Download the file
                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url) as response:
                        file_bytes = await response.read()
                        
                async with aiofiles.tempfile.NamedTemporaryFile(
                    mode="wb", suffix=".tmp", delete=False
                ) as f:
                    temp_path = f.name
                    await f.write(file_bytes)
                
                # We need to simulate the FastAPI /ingest endpoint logic here
                import fitz
                text_content = ""
                doc = fitz.open(temp_path)
                for page in doc: text_content += page.get_text()
                doc.close()
                
                import uuid
                doc_id = str(uuid.uuid4())
                orchestrator.get_or_create_project(doc_id, lob="General")
                
                # 1. Extraction
                await turn_context.send_activity(MessageFactory.text("Extracting Functional Requirements..."))
                ext_result = await orchestrator.run_extraction(doc_id, text_content, context_type="document")
                
                # 2. Gap Analysis & TRD
                await turn_context.send_activity(MessageFactory.text("Executing Adversarial Gap Analysis and Generating TRD..."))
                analysis_results = await orchestrator.run_gap_analysis(doc_id, enabled_modules=['gaps', 'trd'])
                
                # 3. Format and Send Response
                gaps = analysis_results.get("gaps", {}).get("gaps", [])
                
                reply_text = f" **Analysis Complete for {file_name}**\n\n"
                reply_text += f"**Identified {len(gaps)} Technical Gaps:**\n"
                for gap in gaps[:3]: # Show top 3 gaps
                    reply_text += f"-  [{gap.get('impact', 'High')}] {gap.get('title', gap.get('requirement', ''))}: {gap.get('description', gap.get('reason', ''))}\n"
                if len(gaps) > 3:
                    reply_text += f"\n*(and {len(gaps) - 3} more... view full report in the web portal)*\n"
                    
                await turn_context.send_activity(MessageFactory.text(reply_text))
                
                # Optional: Send TRD snippet
                trd_link_msg = "The full TRD and Backlog has been saved to your BA Agent Pro dashboard."
                await turn_context.send_activity(MessageFactory.text(trd_link_msg))

            except Exception as e:
                import traceback
                traceback.print_exc()
                await turn_context.send_activity(MessageFactory.text(f" Error processing document: {str(e)}"))
            finally:
                if temp_path:
                    try:
                        await aiofiles.os.remove(temp_path)
                    except OSError:
                        pass
            return

        # Handle Text Messages (Semantic Knowledge Search)
        text = activity.text.strip() if activity.text else ""
        if text:
            await turn_context.send_activity(MessageFactory.text("Searching Institutional Memory... "))
            try:
                memory_context = await self.knowledge_agent.retrieve_relevant_context(text, lob="General", n_results=3)
                await turn_context.send_activity(MessageFactory.text(memory_context))
            except Exception as e:
                await turn_context.send_activity(MessageFactory.text(f" Error searching memory: {str(e)}"))
