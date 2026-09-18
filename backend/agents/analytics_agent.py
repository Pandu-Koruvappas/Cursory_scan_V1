from services.ado_service import AzureDevOpsService

class AnalyticsAgent:
    def __init__(self):
        self.ado = AzureDevOpsService()

    async def get_sprint_metrics(self):
        """
        Calculates strategic metrics for sprint planning with timeout protection.
        """
        import asyncio
        print(" Calculating sprint planning metrics...")
        try:
            # Wrap the external call in a timeout to prevent 502 crashes
            try:
                items = await asyncio.wait_for(self.ado.get_all_work_items(), timeout=25.0)
            except asyncio.TimeoutError:
                return {"error": "Azure DevOps connection timed out. Please try again."}

            if not items:
                return {"error": "No work items found to analyze."}

            total_items = len(items)
            total_effort = sum([float(i.get("effort", 0)) for i in items])
            
            # Type distribution
            types = {}
            for i in items:
                t = i["type"]
                types[t] = types.get(t, 0) + 1

            # Status distribution
            statuses = {}
            for i in items:
                s = i["status"]
                statuses[s] = statuses.get(s, 0) + 1

            # Sprint Planning Recommendations
            avg_effort = total_effort / total_items if total_items > 0 else 0
            
            return {
                "summary": {
                    "total_work_items": total_items,
                    "total_backlog_effort": total_effort,
                    "average_item_complexity": round(avg_effort, 2)
                },
                "distribution": {
                    "by_type": types,
                    "by_status": statuses
                },
                "planning_insights": [
                    f"Backlog contains {types.get('User Story', 0)} User Stories and {types.get('Bug', 0)} Bugs.",
                    f"Project has {statuses.get('New', 0) + statuses.get('To Do', 0)} unstarted items.",
                    "Recommendation: Focus on 'Must-Have' items for the next sprint cycle."
                ]
            }
        except Exception as e:
            if isinstance(e, BaseExceptionGroup):
                errs = ", ".join([str(x) for x in e.exceptions])
                print(f"WARN: Analytics failed: {errs}")
            else:
                print(f"WARN: Analytics failed: {e}")
            return {"error": str(e)}
