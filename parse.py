#llama3.1:8b
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

template = (
    "You are an expert at extracting and standardizing product information from e-commerce websites. "
    "Given the following text content: {dom_content}\n\n"
    "Instructions:\n"
    "1. Extract and standardize product information in this exact format:\n"
    "   Product Name | Price | Rating | Total Reviews\n"
    "2. Format rules:\n"
    "   - Prices should be in $XX.XX format\n"
    "   - Ratings should be in X.X out of 5 format\n"
    "   - Reviews should be numeric only\n"
    "3. Clean the data:\n"
    "   - Remove any HTML or special characters\n"
    "   - Ensure consistent formatting\n"
    "   - Handle missing values with 'N/A'\n"
    "4. Each product should be on a new line\n"
    "5. Fields must be separated by ' | '\n\n"
    "User request: {parse_description}\n"
    "Extract and format the product information:"
)

model = OllamaLLM(model="llama3.1:8b")

def parse_with_ollama(dom_chunks, parse_description):
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | model

    parsed_results = []

    for i, chunk in enumerate(dom_chunks, start=1):
        print(f"Processing chunk {i} of {len(dom_chunks)}...")
        response = chain.invoke(
            {"dom_content": chunk, "parse_description": parse_description}
        )
        if response and '|' in response:
            parsed_results.append(response)

    return "\n".join(parsed_results)
