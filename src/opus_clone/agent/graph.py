from langgraph.graph import END, START, StateGraph

from opus_clone.agent.nodes.analyze import analyze_node
from opus_clone.agent.nodes.build_edl import build_edl_node
from opus_clone.agent.nodes.prepare import prepare_node
from opus_clone.agent.nodes.render import render_node
from opus_clone.agent.nodes.score import score_node
from opus_clone.agent.nodes.transcribe import transcribe_node
from opus_clone.agent.state import PipelineState
from opus_clone.config import get_settings
from opus_clone.logging import get_logger

logger = get_logger("agent.graph")


def build_graph() -> StateGraph:
    """Build the LangGraph state graph for the video processing pipeline."""
    graph = StateGraph(PipelineState)

    graph.add_node("prepare", prepare_node)
    graph.add_node("transcribe", transcribe_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("score", score_node)
    graph.add_node("build_edl", build_edl_node)
    graph.add_node("render", render_node)

    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "transcribe")
    graph.add_edge("transcribe", "analyze")
    graph.add_edge("analyze", "score")
    graph.add_edge("score", "build_edl")
    graph.add_edge("build_edl", "render")
    graph.add_edge("render", END)

    return graph


async def get_compiled_graph():
    """Get compiled graph with PostgresSaver checkpointer."""
    settings = get_settings()
    graph = build_graph()

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        db_url = settings.database_url.replace("postgres://", "postgresql://", 1)
        checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
        await checkpointer.setup()
        compiled = graph.compile(checkpointer=checkpointer)
        logger.info("graph_compiled_with_checkpointer")
    except Exception as e:
        logger.warning("graph_compiled_without_checkpointer", error=str(e))
        compiled = graph.compile()

    return compiled


async def run_pipeline(source_video_id: str) -> dict:
    """Run the full processing pipeline for a source video."""
    compiled = await get_compiled_graph()

    initial_state: PipelineState = {
        "source_video_id": source_video_id,
        "current_step": "prepare",
    }

    config = {"configurable": {"thread_id": f"pipeline-{source_video_id}"}}

    logger.info("pipeline_start", source_video_id=source_video_id)
    result = await compiled.ainvoke(initial_state, config=config)
    logger.info("pipeline_complete", source_video_id=source_video_id)

    return result
