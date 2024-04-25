import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from bisheng_langchain.vectorstores import ElasticKeywordsSearch
from bisheng_langchain.vectorstores.milvus import Milvus
from langchain_core.documents import Document
from langchain_core.pydantic_v1 import Field
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore

from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from langchain.text_splitter import TextSplitter

from .baseline_vector_retriever import BaselineVectorRetriever

from init_retrievers.extract_info import extract

class KeywordRetriever(BaseRetriever):
    keyword_store: ElasticKeywordsSearch
    text_splitter: TextSplitter
    search_type: str = 'similarity'
    search_kwargs: dict = Field(default_factory=dict)

    def add_documents(
        self,
        documents: List[Document],
        collection_name: str,
        drop_old: bool = False,
        whether_aux_info: bool = False,
        max_length: int = 8000,
    ) -> None:
        split_docs = self.text_splitter.split_documents(documents)
        print(f"KeywordRetriever: split document into {len(split_docs)} chunks")
        aux_info = ''
        if whether_aux_info:
            all_text = ""
            for doc in split_docs:
                all_text = all_text + doc.page_content + "/n"
            aux_info = extract(text=all_text, max_length=max_length)
            print(aux_info)
        for chunk_index, split_doc in enumerate(split_docs):
            if 'chunk_bboxes' in split_doc.metadata:
                split_doc.metadata.pop('chunk_bboxes')
            split_doc.metadata['chunk_index'] = chunk_index
            if aux_info != '':
                split_doc.metadata['aux_info'] = aux_info
                # add key_info into page_content
                split_doc.page_content = split_doc.metadata["source"] + '\n' + aux_info + '\n' + split_doc.page_content
        
        elasticsearch_url = self.keyword_store.elasticsearch_url
        ssl_verify = self.keyword_store.ssl_verify
        self.keyword_store.from_documents(
            split_docs,
            embedding='',
            index_name=collection_name,
            elasticsearch_url=elasticsearch_url,
            ssl_verify=ssl_verify,
            drop_old=drop_old,
        )

    def _get_relevant_documents(
        self,
        query: str,
        collection_name: str,
    ) -> List[Document]:
        self.keyword_store = self.keyword_store.__class__(
            index_name=collection_name,
            elasticsearch_url=self.keyword_store.elasticsearch_url,
            ssl_verify=self.keyword_store.ssl_verify,
        )
        if self.search_type == 'similarity':
            result = self.keyword_store.similarity_search(query, **self.search_kwargs)
        return result
