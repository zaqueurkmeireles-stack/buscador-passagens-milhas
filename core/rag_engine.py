import logging
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
from supabase.client import create_client
from core.config import config

logger = logging.getLogger(__name__)

class RAGEngine:
    """
    Motor de Recuperação de Informação (RAG) conectado à extensão pgvector do Supabase.
    Responsável por ingerir documentos (como vouchers de hotéis) e recuperar contextos
    relevantes para a arquitetura de agentes.
    """
    def __init__(self):
        # Acesso direto ao Supabase existente do projeto
        self.supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        
        # Emprego de Embeddings da OpenAI pela alta acurácia semântica
        if not config.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY não configurada. O RAG pode falhar.")
            
        self.embeddings = OpenAIEmbeddings(api_key=config.OPENAI_API_KEY)
        
        # O SupabaseVectorStore exige que exista a tabela no DB (geralmente "documents")
        # e uma function correspondente (geralmente "match_documents") para o cálculo de cosseno/distância.
        self.vector_store = SupabaseVectorStore(
            embedding=self.embeddings,
            client=self.supabase,
            table_name="documents",
            query_name="match_documents"
        )
        
        # Retorna os 3 blocos mais relevantes
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})

    def ingest_pdf(self, file_path: str):
        """
        Lê um PDF, particiona o texto em chunks e insere no PGVector (Supabase).
        """
        try:
            logger.info(f"Iniciando ingestão e vetorização do documento: {file_path}")
            loader = PyPDFLoader(file_path)
            docs = loader.load_and_split()
            self.vector_store.add_documents(docs)
            logger.info(f"Ingestão concluída com sucesso para: {file_path}")
        except Exception as e:
            logger.error(f"Falha técnica ao ingerir PDF {file_path}: {e}", exc_info=True)
            
    def get_retriever(self):
        """Devolve o objeto retriever para ser usado pelo nó LangGraph."""
        return self.retriever
