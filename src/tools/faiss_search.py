import faiss
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
import pickle
from sentence_transformers import SentenceTransformer

from ..utils.logging_config import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class FAISSSearchEngine:
    """
    Semantic search engine для поиска похожих финансовых отчетов
    
    Features:
    - FAISS index для fast similarity search
    - SentenceTransformer embeddings (multilingual)
    - Metadata хранение для результатов
    - Batch indexing для масштабируемости
    """
    
    def __init__(
        self,
        index_path: Path,
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    ):
        """
        Args:
            index_path: Путь к FAISS индексу
            embedding_model: Модель для embeddings
        """
        self.index_path = Path(index_path)
        self.embedding_model_name = embedding_model
        
        # Инициализация embedding модели
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        
        # Загрузка или создание индекса
        self.index, self.metadata = self._load_or_create_index()
        
        logger.info(
            f"FAISS index ready: {self.index.ntotal} documents indexed"
        )
    
    def _load_or_create_index(self):
        """Загрузка существующего индекса или создание нового"""
        index_file = self.index_path / "faiss_index.bin"
        metadata_file = self.index_path / "metadata.pkl"
        
        if index_file.exists() and metadata_file.exists():
            # Загрузка существующего
            logger.info("Loading existing FAISS index")
            index = faiss.read_index(str(index_file))
            
            with open(metadata_file, 'rb') as f:
                metadata = pickle.load(f)
            
            return index, metadata
        else:
            # Создание нового
            logger.info("Creating new FAISS index")
            self.index_path.mkdir(parents=True, exist_ok=True)
            
            # IndexFlatIP для cosine similarity
            index = faiss.IndexFlatIP(self.embedding_dim)
            metadata = []
            
            return index, metadata
    
    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 32
    ) -> int:
        """
        Добавление документов в индекс
        
        Args:
            documents: List с документами, каждый Dict должен содержать:
                - 'text': str - текст для индексации
                - 'metadata': dict - метаданные (company, date, type)
            batch_size: Размер батча для embeddings
        
        Returns:
            Количество добавленных документов
        """
        if not documents:
            return 0
        
        logger.info(f"Indexing {len(documents)} documents...")
        
        # Извлечение текстов
        texts = [doc['text'] for doc in documents]
        
        # Генерация embeddings батчами
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            embeddings = self.embedding_model.encode(
                batch_texts,
                show_progress_bar=True,
                normalize_embeddings=True  # Для cosine similarity
            )
            all_embeddings.extend(embeddings)
        
        # Конвертация в numpy
        embeddings_np = np.array(all_embeddings).astype('float32')
        
        # Добавление в FAISS
        self.index.add(embeddings_np)
        
        # Сохранение метаданных
        for doc in documents:
            self.metadata.append(doc.get('metadata', {}))
        
        # Сохранение индекса
        self._save_index()
        
        logger.info(f"✅ Indexed {len(documents)} documents")
        return len(documents)
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Семантический поиск похожих документов
        
        Args:
            query: Текстовый запрос
            top_k: Количество результатов
            min_similarity: Минимальный порог similarity (0.0-1.0)
        
        Returns:
            List результатов с метаданными и scores
        """
        if self.index.ntotal == 0:
            logger.warning("FAISS index is empty")
            return []
        
        # Генерация embedding для запроса
        query_embedding = self.embedding_model.encode(
            [query],
            normalize_embeddings=True
        ).astype('float32')
        
        # Поиск в FAISS
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Формирование результатов
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score < min_similarity:
                continue
            
            if 0 <= idx < len(self.metadata):
                result = {
                    'score': float(score),
                    'metadata': self.metadata[idx],
                    'index': int(idx)
                }
                results.append(result)
        
        logger.info(f"Found {len(results)} results for query: '{query[:50]}...'")
        return results
    
    def _save_index(self):
        """Сохранение индекса и метаданных"""
        index_file = self.index_path / "faiss_index.bin"
        metadata_file = self.index_path / "metadata.pkl"
        
        faiss.write_index(self.index, str(index_file))
        
        with open(metadata_file, 'wb') as f:
            pickle.dump(self.metadata, f)
        
        logger.info("FAISS index saved")
    
    def clear_index(self):
        """Очистка индекса"""
        self.index.reset()
        self.metadata = []
        logger.info("FAISS index cleared")
