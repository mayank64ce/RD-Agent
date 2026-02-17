You are an expert in OpenFHE C++ programming. Your task is to implement the body of the `eval()` function for an FHE challenge.

## Algorithm Plan

{algorithm_plan}

## Challenge Summary

{challenge_summary}

## Variable Names — Use EXACTLY These

```
{variable_names}
```

**CRITICAL RULES:**
- `eval()` is a **void** function — you MUST assign your result to the output ciphertext variable, do NOT use `return`
- Use the EXACT member variable names shown above (e.g., `m_cc`, `m_InputC`, `m_OutputC`)
- Do NOT declare new `CryptoContext` or load keys — they are already initialized
- Do NOT include the function signature (`void ClassName::eval()`) — output ONLY the body

## Previous Feedback

{feedback}

## Challenge Type

{challenge_type}

---

## Required Output Format

Output the `eval()` function body in a C++ code block:

```cpp
// Your implementation here
// Example (replace with actual algorithm):
auto result = m_cc->EvalAdd(m_InputC, m_InputC);
m_OutputC = result;
```

For **white_box** challenges only, you may optionally provide updated crypto parameters in a JSON block:

```json
{{
  "mult_depth": 20,
  "indexes_for_rotation_key": [1, 2, 4, 8],
  "scale_mod_size": 50
}}
```

**Important notes:**
- Only include parameter changes that are necessary for your algorithm
- The `mult_depth` must be sufficient for your multiplicative depth
- Include rotation indices only if you use `EvalRotate`
- Do NOT change the encryption scheme unless the challenge allows it
