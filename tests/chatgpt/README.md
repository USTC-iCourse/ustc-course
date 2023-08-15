## Power iCourse.club with ChatGPT

### Why?

Although most reviews in iCourse.club are public, ChatGPT and New Bing do not provide satisfactory questions answering
experience regarding courses and teachers in XJTU.

ChatGPT cannot answer the questions simply because their (GPT-3.5 and GPT-4) training datasets do not include
iCourse.club.

New Bing can answer simple factual questions correctly, for example, "Which teachers teach course XXX in XJTU?" and it
typically gives reference to iCourse.club. However, for subjective questions such as "Which teachers are good at
teaching course XXX in XJTU?" and "Does teacher YYY's course XXX have a good name outside?", New Bing can only provide
rough answers without much details. It may even provide incorrect sentiment. For example, some courses such as Physics
Experiments and Quantum Physics for CS department are notorious in the reviews, but New Bing considers them as good
courses and gives references to webpages full of bad reviews!

We find that by manually crafting prompts made of snippets of reviews, ChatGPT (GPT-3.5) can actually do much better
than New Bing and produce meaningful answers to course-related questions. So we initiate this preliminary project to
grant iCourse.club the ability to answer questions and provide advice on course selection.

### Preparation

1. Invoke the OpenAI Embeddings API to extract embeddings for all public reviews (reviews that are not hidden, blocked
   or only visible to login students), and store the embeddings in a vector database (currently we use Milvus).
2. Create a keyword-based index for all public reviews (for example, using ElasticSearch). The keyword-based index
   complements the embedding-based index as embeddings capture the overall semantics of the review while keyword-based
   search captures the details.
3. Utilize the OpenAI Completion API to create a text summary for all public reviews in each course, and put into the
   aforementioned indexes (embedding and keyword). The text summary aims to simplify answering questions like "Which
   teachers are good at teaching course XXX?" and "Which courses do teacher YYY teach, and how about the reviews?". Due
   to the token limit of one OpenAI query, if we do not have pre-summarized text for each course, it would require
   multiple OpenAI queries to summarize the reviews of each course, which is not only expensive but also introduces
   significant latency (roughly 20 seconds).

### Question Answering

We would build an UI to enable the users interact with icourse.club like ChatGPT.

When a prompt is received from the user:

1. Invoke the OpenAI Embeddings API to extract the embeddings of the prompt.
2. Find the top N matching reviews or course review summaries in the vector database and keyword-based index, and
   concatenate them together to fit in the token limit.
3. Invoke the OpenAI Completion API by prompting it to answer the user's question according to the reviews and
   summaries.
4. Stream the response to the UI.

When a user publishes or updates a review, we insert or update the embedding of the review, and update the text summary
of the course.

### Challenges

1. How to find the most relevant reviews and summaries for a given user prompt?
2. How to prompt the OpenAI Completion API such that the responses contain references to the reviews, like what New Bing
   has achieved?

### Future Work

This approach can be extended to other sources of data, for example webpages in XJTU (`*.ustc.edu.cn`).

We have crawled 207K web pages from `*.ustc.edu.cn`. After tuning the question answering engine for iCourse reviews, we
can move further to generic webpages which is more challenging.

### Feel free to contact us if you want to join us!
