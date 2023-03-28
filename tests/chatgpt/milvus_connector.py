import time

import numpy as np
from pymilvus import (
    connections,
    utility,
    FieldSchema, CollectionSchema, DataType,
    Collection,
)

fmt = "\n=== {:30} ===\n"
dim = 1536    # the dim for text-embedding-ada-002

print(fmt.format("start connecting to Milvus"))
connections.connect("default", host="hwcloud-vpc.ring0.me", port="19530")

has = utility.has_collection("icourse_reviews")
print(f"Does collection icourse_reviews exist in Milvus: {has}")

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
    FieldSchema(name="course_id", dtype=DataType.INT64),
    FieldSchema(name="author_id", dtype=DataType.INT64),
    FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=dim)
]

schema = CollectionSchema(fields, "get the embeddings of icourse reviews")

milvus_collection = Collection("icourse_reviews", schema, consistency_level="Strong")
print(fmt.format("Created collection `icourse_reviews`"))

print("Start creating index in Milvus...")
index = {
    "index_type": "FLAT",
    "metric_type": "L2",
    "params": {}
}

if len(milvus_collection.indexes) == 0:
    milvus_collection.create_index("embeddings", index)

milvus_collection.load()
