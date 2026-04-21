import sqlite3
import math
import struct
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class QueryResult:
    id: int
    content: str
    similarity: float
    labels: List[str]


class VectorDatabase:
    """支持标签过滤的向量数据库，优化内存存储结构"""

    def __init__(self):
        self.vectors_array = None  # np.array shape=(N, d)
        self.norms_array = None  # np.array shape=(N,)
        self.ids_array = None  # np.array shape=(N,)
        self.label_index = defaultdict(set)  # {label: set(row_index)}
        self.id_labels = defaultdict(set)  # {id: set(labels)}
        self.content_dict = {}  # {id: content}
        self.dimension = 0

    def load_from_sqlite(self, conn: sqlite3.Connection):
        """从SQLite加载数据和标签索引"""
        # 加载向量数据
        cursor = conn.execute("SELECT id, vector, content, norm FROM vectors")
        vector_data = cursor.fetchall()

        if not vector_data:
            return

        # 初始化numpy数组
        sample_vec = self.deserialize_vector(vector_data[0][1])
        self.dimension = len(sample_vec)
        N = len(vector_data)

        self.vectors_array = np.empty((N, self.dimension), dtype=np.float32)
        self.norms_array = np.empty(N, dtype=np.float32)
        self.ids_array = np.empty(N, dtype=np.int64)

        # 构建内存结构
        row_index_mapping = {}
        for i, (id_, vec_blob, content, norm) in enumerate(vector_data):
            self.vectors_array[i] = self.deserialize_vector(vec_blob)
            self.norms_array[i] = norm
            self.ids_array[i] = id_
            self.content_dict[id_] = content
            row_index_mapping[id_] = i

        # 加载标签数据并构建索引
        cursor = conn.execute("SELECT vector_id, label FROM labels")
        for vector_id, label in cursor:
            self.id_labels[vector_id].add(label)
            if vector_id in row_index_mapping:
                row_idx = row_index_mapping[vector_id]
                self.label_index[label].add(row_idx)

    def search(
            self,
            query_vec: List[float],
            top_k: int = 100,  # 设置默认top_k为100
            target_labels: Optional[List[str]] = None,
            exclude_labels: Optional[List[str]] = None,
            top_p: float = None  # 相似度阈值参数
    ) -> List[QueryResult]:
        """带标签过滤和相似度阈值过滤的向量搜索"""
        if self.vectors_array is None or len(self.vectors_array) == 0:
            return []

        # 生成候选索引：初始为所有索引
        candidate_indices = set(range(len(self.ids_array)))
        indices = None

        # 应用包含标签过滤 - 必须包含所有指定标签 (AND关系)
        if target_labels and len(target_labels) > 0:
            valid_labels = [label for label in target_labels if label in self.label_index]

            # 如果存在无效标签，直接返回空结果（因为要求必须包含所有标签）
            if len(valid_labels) < len(target_labels):
                return []

            # 获取包含所有目标标签的索引
            for label in target_labels:
                if candidate_indices:  # 仅当候选集不为空时才继续
                    candidate_indices &= self.label_index[label]
                else:
                    break  # 候选集已为空，提前退出

        # 应用排除标签过滤 - 不能包含任何排除标签 (NOT OR关系)
        if exclude_labels and len(exclude_labels) > 0:
            # 获取包含任何排除标签的索引
            excluded_indices = set()
            for label in exclude_labels:
                if label in self.label_index:
                    excluded_indices |= self.label_index[label]

            # 从候选集中移除包含任何排除标签的项
            candidate_indices -= excluded_indices

        # 处理空候选集
        if not candidate_indices:
            return []
        indices = np.array(list(candidate_indices))

        # 向量计算
        query_np = np.array(query_vec, dtype=np.float32)
        query_norm = np.linalg.norm(query_np)

        # 批量计算余弦相似度
        filtered_vectors = self.vectors_array[indices]
        filtered_norms = self.norms_array[indices]
        dot_products = np.dot(filtered_vectors, query_np)
        similarities = dot_products / (filtered_norms * query_norm)

        # 应用top_p阈值过滤
        if top_p is not None:
            # 创建一个布尔掩码，标识哪些相似度达到阈值
            above_threshold = similarities >= top_p

            # 过滤出达到阈值的索引
            indices = indices[above_threshold]
            similarities = similarities[above_threshold]

        # 检查过滤后的结果是否为空
        if len(similarities) == 0:
            return []

        # 安全处理top_k值
        effective_top_k = min(top_k, len(similarities))

        # 获取TopK结果
        if effective_top_k >= len(similarities):
            # 如果需要所有结果，直接排序
            sorted_indices = np.argsort(-similarities)
        else:
            # 否则使用argpartition
            top_indices = np.argpartition(-similarities, effective_top_k)[:effective_top_k]
            sorted_indices = top_indices[np.argsort(-similarities[top_indices])]

        # 构建返回结果
        results = []
        for idx in sorted_indices:
            vec_id = int(self.ids_array[indices[idx]])
            results.append(QueryResult(
                id=vec_id,
                content=self.content_dict[vec_id],
                similarity=float(similarities[idx]),
                labels=list(self.id_labels.get(vec_id, set()))
            ))

        return results[:top_k]  # 确保返回不超过请求的top_k

    @staticmethod
    def serialize_vector(vec: List[float]) -> bytes:
        return struct.pack(f'!{len(vec)}f', *vec)

    @staticmethod
    def deserialize_vector(data: bytes) -> List[float]:
        return list(struct.unpack(f'!{len(data) // 4}f', data))

    @staticmethod
    def norm(vec: List[float]) -> float:
        return math.sqrt(sum(x * x for x in vec))


class SQLiteOptimizer:
    """SQLite性能优化配置类"""

    @staticmethod
    def configure_connection(conn: sqlite3.Connection):
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA mmap_size=2684354560")  # 2560MB
        conn.execute("PRAGMA cache_size=-100000")  # 100MB
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA temp_store=MEMORY")


class RAGService:
    """支持标签过滤的RAG服务"""

    def __init__(self, db_path: str, cache_size: int = 1024):
        self.db_path = Path(db_path)
        if self.db_path.suffix != '.db':
            self.db_path = self.db_path / "rag.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_size = cache_size  # 单位MB
        self.vector_db = VectorDatabase()
        self._prepare_statements()
        self.create_knowledge_base()
        self._load_data_to_memory()

    def _prepare_statements(self):
        self.create_kb_sql = """
            CREATE TABLE IF NOT EXISTS vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vector BLOB NOT NULL,
                content TEXT NOT NULL,
                norm REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS labels (
                vector_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                FOREIGN KEY(vector_id) REFERENCES vectors(id)
            );
            CREATE INDEX IF NOT EXISTS idx_labels ON labels(vector_id, label);
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_search USING fts5(
                content,
                content_rowid='id',
                tokenize='porter unicode61'
            );
        """

        self.insert_sql = """
            INSERT INTO vectors (vector, content, norm) 
            VALUES (?, ?, ?)
        """

    def _load_data_to_memory(self):
        """带内存限制的加载策略"""
        with self._get_connection() as conn:
            # 计算预估内存占用
            row_count = conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
            estimated_size = row_count * (1024 + 512)  # 预估每条记录约1.5KB

            if estimated_size > self.cache_size * 1024 * 1024:
                raise MemoryError(f"预估需要{estimated_size // (1024 * 1024)}MB内存，超过缓存限制{self.cache_size}MB")

            self.vector_db.load_from_sqlite(conn)

    def _get_connection(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(str(self.db_path))
            SQLiteOptimizer.configure_connection(conn)
            return conn
        except sqlite3.Error as e:
            raise RuntimeError(f"无法打开数据库 {self.db_path}: {str(e)}")

    def create_knowledge_base(self):
        try:
            with self._get_connection() as conn:
                conn.executescript(self.create_kb_sql)
        except sqlite3.Error as e:
            raise RuntimeError(f"创建知识库失败: {str(e)}")

    def delete_knowledge_base(self):
        try:
            if self.db_path.exists():
                self.db_path.unlink()
        except OSError as e:
            raise RuntimeError(f"删除知识库失败: {str(e)}")

    def insert_data(self, data: List[Tuple[List[float], str, List[str]]]):
        """批量插入带标签的数据"""
        if not data:
            return

        vector_records = []
        label_records = []

        # 准备数据
        for vec, content, labels in data:
            vec_blob = VectorDatabase.serialize_vector(vec)
            norm = VectorDatabase.norm(vec)
            vector_records.append((vec_blob, content, norm))
            label_records.append(labels)

        with self._get_connection() as conn:
            # 插入向量数据
            conn.executemany(self.insert_sql, vector_records)

            # 获取批量插入的ID范围
            last_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            start_id = last_id - len(data) + 1

            # 插入标签数据
            labels_to_insert = []
            for i, labels in enumerate(label_records):
                vec_id = start_id + i
                for label in labels:
                    labels_to_insert.append((vec_id, label))

            if labels_to_insert:
                conn.executemany(
                    "INSERT INTO labels (vector_id, label) VALUES (?, ?)",
                    labels_to_insert
                )

            # 更新全文索引
            conn.execute("""
                INSERT INTO vec_search(rowid, content)
                SELECT id, content FROM vectors 
                WHERE id BETWEEN ? AND ?
            """, (start_id, last_id))

        self._load_data_to_memory()

    def search_data(
            self,
            query_vec: List[float],
            top_k: int = 100,  # 设置默认值100
            target_labels: Optional[List[str]] = None,
            exclude_labels: Optional[List[str]] = None,
            top_p: float = None  # 相似度阈值参数
    ) -> List[QueryResult]:
        """带标签过滤和相似度阈值过滤的向量搜索"""
        return self.vector_db.search(
            query_vec,
            top_k,
            target_labels=target_labels,
            exclude_labels=exclude_labels,
            top_p=top_p
        )

    def delete_data(self, ids: List[int]):
        """批量删除数据"""
        if not ids:
            return

        placeholders = ','.join(['?'] * len(ids))
        try:
            with self._get_connection() as conn:
                # 删除向量数据
                conn.execute(f"""
                    DELETE FROM vectors 
                    WHERE id IN ({placeholders})
                """, ids)

                # 删除标签数据
                conn.execute(f"""
                    DELETE FROM labels 
                    WHERE vector_id IN ({placeholders})
                """, ids)

                # 删除全文索引
                conn.execute(f"""
                    DELETE FROM vec_search 
                    WHERE rowid IN ({placeholders})
                """, ids)

            self._load_data_to_memory()
        except sqlite3.Error as e:
            raise RuntimeError(f"删除数据失败: {str(e)}")

    def optimize_database(self):
        """执行数据库优化维护"""
        try:
            with self._get_connection() as conn:
                conn.execute("REINDEX")
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
            self._load_data_to_memory()
        except sqlite3.Error as e:
            raise RuntimeError(f"数据库优化失败: {str(e)}")

import time
from pathlib import Path
from src.core.common.config_manager import DATA_PATH
# 使用示例
if __name__ == "__main__":
    rag = RAGService(db_path=DATA_PATH / "rag_data/tech.db", cache_size=512)

    # 插入测试数据
    sample_data = [
        ([0.8 if i < 200 else 0.1 for i in range(1024)], "人工智能核心技术综述",
         ["AI", "科技", "理论"]),
        ([0.7 if 200 <= i < 300 else 0.2 for i in range(1024)], "SQLite高级优化指南",
         ["数据库", "优化", "实践"]),
        ([0.9 if 300 <= i < 450 else 0.1 for i in range(1024)], "基于Transformer的大模型研究",
         ["AI", "深度学习", "理论"]),
        ([0.6 if 450 <= i < 500 else 0.3 for i in range(1024)], "Python异步编程实战",
         ["编程", "Python", "实践"]),
        ([0.7 if 500 <= i < 600 else 0.1 for i in range(1024)], "线性代数在机器学习中的应用",
         ["数学", "机器学习", "理论"]),
    ]
    # rag.insert_data(sample_data)

    # 测试1：默认搜索（没有标签过滤）
    print("测试1：默认搜索")
    results = rag.search_data(
        query_vec=[0.8 if 400 <= i < 550 else 0.2 for i in range(1024)],
        top_k = 2
    )
    for r in results:
        print(f"ID:{r.id} 相似度:{r.similarity:.4f} 标签:{r.labels}")

    # 测试2：必须包含所有指定标签（AND关系）
    print("\n测试2：必须包含所有指定标签")
    results = rag.search_data(
        query_vec=[0.8 if 400 <= i < 550 else 0.2 for i in range(1024)],
        target_labels=["AI", "理论"]  # 必须同时包含这两个标签
    )
    for r in results:
        print(f"ID:{r.id} 标签:{r.labels} 相似度:{r.similarity:.4f}")

    # 测试3：排除标签（不能包含任何排除标签）
    print("\n测试3：排除标签")
    results = rag.search_data(
        query_vec=[0.8 if 400 <= i < 550 else 0.2 for i in range(1024)],
        exclude_labels=["实践"]  # 不能包含"实践"标签
    )
    for r in results:
        print(f"ID:{r.id} 标签:{r.labels} 相似度:{r.similarity:.4f}")

    # 测试4：组合使用标签过滤和相似度阈值
    print("\n测试4：组合过滤")
    results = rag.search_data(
        query_vec=[0.8 if 400 <= i < 550 else 0.2 for i in range(1024)],
        target_labels=["理论", "数学"],
        exclude_labels=["深度学习", "AI"],
        top_p=0.5  # 相似度必须≥0.82
    )
    for r in results:
        print(f"ID:{r.id} 标签:{r.labels} 相似度:{r.similarity:.4f}")

    # 清理测试数据
    # rag.delete_data([r.id for r in results])