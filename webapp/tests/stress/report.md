# PPLLM Assistant stress test

Answer reached the model: **before 35/54**, **after 52/54**

## Documents
| File | Extraction |
|---|---|
| article_ligatures.pdf | 4 pages, 9812 chars, 17 chunks, quality check: ok |
| article_single_column.pdf | 4 pages, 9878 chars, 17 chunks, quality check: ok |
| article_two_column.pdf | 4 pages, 10158 chars, 19 chunks, quality check: ok |
| long_report_40_sections.pdf | 13 pages, 40203 chars, 112 chunks, quality check: ok |
| news_saved_from_browser.pdf | 1 pages, 1583 chars, 3 chunks, quality check: ok |
| password_protected.pdf | EXTRACTION FAILED: This PDF is password-protected. Open it, save a copy without a password (or use Print to PDF), and upload that copy. |
| scanned_memo.pdf | 1 pages, 0 chars, 0 chunks, quality check: empty ("This file has almost no readable text. It is probably a scan or a picture of a page. Take a screenshot of the page and upload it as an image (PNG or JPG) so the app can read it with OCR.") |
| slides_exported.pdf | 4 pages, 320 chars, 1 chunks, quality check: thin ("This document is very short, so the Assistant can only answer questions about these few lines.") |
| spanish_article.pdf | 1 pages, 313 chars, 1 chunks, quality check: thin ("This document is very short, so the Assistant can only answer questions about these few lines.") |
| table_heavy.pdf | 1 pages, 200 chars, 1 chunks, quality check: thin ("This document is very short, so the Assistant can only answer questions about these few lines.") |
| tiny_memo.pdf | 1 pages, 85 chars, 1 chunks, quality check: thin ("This document is very short, so the Assistant can only answer questions about these few lines.") |

## Questions
| File | Question | Before (mode/passages) | Before | After | After |
|---|---|---|---|---|---|
| article_ligatures.pdf | What were the findings? | keyword/0 | **NO** | section/3 | yes |
| article_ligatures.pdf | What is the reconciliation error rate? | keyword/3 | yes | keyword/3 | yes |
| article_ligatures.pdf | What are the main findings? | keyword/1 | **NO** | section/3 | yes |
| article_single_column.pdf | What is this paper about? | overview/5 | yes | overview/5 | yes |
| article_single_column.pdf | Summarize the article | overview/5 | yes | overview/5 | yes |
| article_single_column.pdf | How many analysts were in the experiment? | keyword/4 | yes | keyword/5 | yes |
| article_single_column.pdf | What methods did the authors use? | section/3 | yes | section/3 | yes |
| article_single_column.pdf | What are the main findings? | keyword/5 | yes | section/3 | yes |
| article_single_column.pdf | What were the results? | keyword/2 | **NO** | section/3 | yes |
| article_single_column.pdf | How much did the error rate fall? | keyword/3 | yes | keyword/3 | yes |
| article_single_column.pdf | What are the limitations of the study? | section/1 | **NO** | section/2 | yes |
| article_single_column.pdf | What should managers do? | keyword/1 | yes | keyword/1 | yes |
| article_single_column.pdf | Who benefits most from AI? | keyword/3 | yes | keyword/4 | yes |
| article_single_column.pdf | What does the conclusion say? | overview/5 | **NO** | section/1 | yes |
| article_single_column.pdf | Did workers become more efficient? | keyword/1 | yes | keyword/2 | yes |
| article_single_column.pdf | What's the takeaway? | overview/5 | yes | overview/5 | yes |
| article_single_column.pdf | Who wrote it? | keyword/0 | **NO** | fallback/5 | yes |
| article_single_column.pdf | What are the limitations? Who wrote it? | section/1 | **NO** | section/6 | yes |
| article_single_column.pdf | What are the limitations? Who wrote it? | section/1 | **NO** | section/6 | yes |
| article_two_column.pdf | What is this paper about? | overview/5 | yes | overview/5 | yes |
| article_two_column.pdf | Summarize the article | overview/5 | yes | overview/5 | yes |
| article_two_column.pdf | How many analysts were in the experiment? | keyword/4 | yes | keyword/5 | yes |
| article_two_column.pdf | What methods did the authors use? | section/3 | **NO** | section/3 | yes |
| article_two_column.pdf | What are the main findings? | keyword/5 | **NO** | section/3 | yes |
| article_two_column.pdf | What were the results? | keyword/2 | **NO** | section/3 | yes |
| article_two_column.pdf | How much did the error rate fall? | keyword/3 | yes | keyword/3 | yes |
| article_two_column.pdf | What are the limitations of the study? | section/2 | yes | section/3 | yes |
| article_two_column.pdf | What should managers do? | keyword/1 | yes | keyword/1 | yes |
| article_two_column.pdf | Who benefits most from AI? | keyword/3 | yes | keyword/4 | yes |
| article_two_column.pdf | What does the conclusion say? | section/1 | **NO** | section/2 | yes |
| article_two_column.pdf | Did workers become more efficient? | keyword/1 | yes | keyword/2 | yes |
| article_two_column.pdf | What's the takeaway? | overview/5 | yes | overview/5 | yes |
| article_two_column.pdf | Who wrote it? | keyword/0 | **NO** | fallback/5 | yes |
| article_two_column.pdf | What are the limitations? Who wrote it? | section/2 | yes | section/7 | yes |
| article_two_column.pdf | What are the limitations? Who wrote it? | section/2 | **NO** | section/7 | yes |
| long_report_40_sections.pdf | How many businesses reported ransomware? | keyword/5 | yes | keyword/5 | yes |
| long_report_40_sections.pdf | What was the median recovery cost? | keyword/1 | yes | keyword/1 | yes |
| long_report_40_sections.pdf | What is this report about? | keyword/0 | **NO** | overview/5 | yes |
| news_saved_from_browser.pdf | How does Jev play Doom? | keyword/3 | yes | whole/3 | yes |
| news_saved_from_browser.pdf | How fast is Jev? | keyword/3 | yes | whole/3 | yes |
| news_saved_from_browser.pdf | What was the confidence threshold? | keyword/1 | yes | whole/3 | yes |
| news_saved_from_browser.pdf | Did the agent finish the level? | keyword/2 | yes | whole/3 | yes |
| news_saved_from_browser.pdf | Summarize this | overview/3 | yes | whole/3 | yes |
| news_saved_from_browser.pdf | Why is a language model worse for this? | keyword/1 | yes | whole/3 | yes |
| password_protected.pdf | Where is the workshop? | keyword/0 | **NO** | keyword/0 | **NO** |
| scanned_memo.pdf | Can students use AI? | keyword/0 | **NO** | keyword/0 | **NO** |
| slides_exported.pdf | Why do models hallucinate? | keyword/1 | yes | whole/1 | yes |
| slides_exported.pdf | How long is a token? | keyword/1 | yes | whole/1 | yes |
| spanish_article.pdf | How many students were surveyed? | keyword/0 | **NO** | whole/1 | yes |
| spanish_article.pdf | ¿Cuántos estudiantes fueron encuestados? | keyword/1 | yes | whole/1 | yes |
| table_heavy.pdf | What was software revenue in Q4? | keyword/1 | yes | whole/1 | yes |
| table_heavy.pdf | Which segment earned the most? | keyword/1 | yes | whole/1 | yes |
| tiny_memo.pdf | Where is the workshop? | keyword/1 | yes | whole/1 | yes |
| tiny_memo.pdf | When is it? | keyword/0 | **NO** | whole/1 | yes |