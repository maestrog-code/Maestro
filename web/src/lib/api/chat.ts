import { useChatStore } from "@/store/useChatStore";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const delay = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException("Aborted", "AbortError"));
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    signal?.addEventListener("abort", onAbort);
  });

async function runSimulatedChatStream(
  prompt: string,
  signal: AbortSignal,
  assistantMsgId: string
) {
  const store = useChatStore.getState();
  console.info("[Simulation Mode] Enabled - Backend unreachable. Running simulated multi-agent stream.");
  store.setIsSimulationMode(true);
  store.clearSubAgentStreams();

  try {
    store.setAgentState("CEO: Decomposing task & initializing team...");
    await delay(1200, signal);

    store.updateScratchpad({
      step: "Decompose query & delegate tasks",
      status: "COMPLETED",
      notes: "CEO planned: delegated finance to CFO, operations to COO."
    });
    
    store.updateScratchpad({
      step: "CFO: Fetch financial trends & metrics",
      status: "IN_PROGRESS",
      notes: "Running financial audit tool..."
    });
    store.setAgentState("CEO delegated to CFO...");
    store.updateToolStatus({ tool_name: "fetch_financial_metrics", status: "running" });
    store.appendSubAgentToken("CFO", "[System] CFO Agent initialized.\n");
    await delay(500, signal);
    store.appendSubAgentToken("CFO", "Fetching gross revenue and operational cost metrics...\n");
    await delay(1000, signal);

    store.updateToolStatus({ tool_name: "fetch_financial_metrics", status: "completed" });
    store.updateToolStatus({ tool_name: "calculate_projected_margins", status: "running" });
    store.updateScratchpad({
      step: "CFO: Fetch financial trends & metrics",
      status: "IN_PROGRESS",
      notes: "Calculating margin projections..."
    });
    store.appendSubAgentToken("CFO", "Gross revenue found: $478,500 (+6.3% variance).\n");
    await delay(600, signal);
    store.appendSubAgentToken("CFO", "Calculating operating margins vs target (22.0%)...\n");
    await delay(600, signal);

    store.updateToolStatus({ tool_name: "calculate_projected_margins", status: "completed" });
    store.updateScratchpad({
      step: "CFO: Fetch financial trends & metrics",
      status: "COMPLETED",
      notes: "Margins calculated: 24.5% actual vs 22% target."
    });
    store.appendSubAgentToken("CFO", "Operating margin calculated: 24.5% (Actual) vs 22.0% (Target). CFO analysis completed successfully.\n");

    store.updateScratchpad({
      step: "COO: Verify operations & resource allocation",
      status: "IN_PROGRESS",
      notes: "Auditing engineer resource utilization..."
    });
    store.setAgentState("CEO delegated to COO...");
    store.updateToolStatus({ tool_name: "check_resource_allocation", status: "running" });
    store.appendSubAgentToken("COO", "[System] COO Agent initialized.\n");
    await delay(600, signal);
    store.appendSubAgentToken("COO", "Accessing active workspace telemetry & engineering logs...\n");
    await delay(1200, signal);

    store.updateToolStatus({ tool_name: "check_resource_allocation", status: "completed" });
    store.updateScratchpad({
      step: "COO: Verify operations & resource allocation",
      status: "COMPLETED",
      notes: "Capacity verified: 92% utilization, 8% buffer."
    });
    store.appendSubAgentToken("COO", "Resource utilization verified: 92% active, 8% capacity buffer. Backlog status: Stable. COO operations audit completed.\n");

    store.updateScratchpad({
      step: "CEO: Consolidate briefings & draft executive response",
      status: "IN_PROGRESS",
      notes: "Synthesizing response report..."
    });
    store.setAgentState("CEO: Summarizing team responses...");
    await delay(1000, signal);

    // Stream response tokens
    const text = `### Executive Briefing: Q2 Operations & Financial Outlook

I have coordinated with our **CFO** (Financial Analysis) and **COO** (Operations) to compile the requested analysis. Here is our consolidated briefing:

#### 1. Financial Performance Analysis (CFO)
Our financial tools retrieved the current Q2 performance metrics. We observed a strong revenue trend driven by a **14.2% increase** in contract size:
| Metric | Target | Actual | Variance |
| :--- | :--- | :--- | :--- |
| **Gross Revenue** | $450,000 | $478,500 | +6.3% |
| **Operating Margin**| 22.0% | 24.5% | +2.5% |
| **Customer LTV** | $8,500 | $9,750 | +14.7% |

#### 2. Operations & Capacity Review (COO)
Resource allocation has been cross-referenced with our active pipeline. While engineering bandwidth is currently at **92% utilization**, we have sufficient buffer to onboard up to two more concurrent enterprise projects.

#### 3. Strategic Guidance (CEO Summary)
* **Capital Allocation:** Reinvest the Q2 revenue surplus into our automated sales pipeline to accelerate pipeline velocity.
* **Hiring Pipeline:** Initiate a search for a Senior Backend Engineer by mid-Q3 to relieve pressure on the core systems team.

Let me know if you would like me to task the **CFO** to run a detailed cash flow projection based on these figures.`;

    const tokens = text.split(" ");
    for (let i = 0; i < tokens.length; i++) {
      const nextWord = tokens[i] + (i === tokens.length - 1 ? "" : " ");
      store.appendTokenToLastAssistantMessage(nextWord);
      // Vary delay slightly to feel realistic
      const delayTime = 30 + Math.random() * 50;
      await delay(delayTime, signal);
    }

    store.updateScratchpad({
      step: "CEO: Consolidate briefings & draft executive response",
      status: "COMPLETED",
      notes: "Draft completed and presented."
    });

  } catch (err: any) {
    if (err.name === "AbortError") {
      console.log("Simulated stream aborted");
    } else {
      console.error("Simulation error:", err);
    }
  } finally {
    store.resetStreamState();
  }
}

export async function sendChatMessage(
  orgId: string,
  prompt: string,
  signal: AbortSignal
) {
  const store = useChatStore.getState();
  store.setIsStreaming(true);
  store.setIsSimulationMode(false);
  store.clearSubAgentStreams();

  // Optimistically add the user message
  store.addMessage({
    id: crypto.randomUUID(),
    role: "user",
    content: prompt,
  });

  const assistantMessageId = crypto.randomUUID();
  // Add an empty assistant message that we will append tokens to
  store.addMessage({
    id: assistantMessageId,
    role: "assistant",
    content: "",
  });
  store.setStreamingMessageId(assistantMessageId);

  store.setAgentState("Initializing...");

  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/organizations/${orgId}/ai/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: prompt }), // Corrected schema key: "message" instead of "prompt"
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }

    if (!response.body) {
      throw new Error("No response body stream");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";

      for (const rawEvent of events) {
        if (!rawEvent.trim()) continue;

        const lines = rawEvent.split("\n");
        let eventType = "";
        let eventData = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.replace("event: ", "").trim();
          } else if (line.startsWith("data: ")) {
            eventData = line.replace("data: ", "").trim();
          }
        }

        if (eventType === "end") {
          store.resetStreamState();
          return;
        }

        if (!eventData || eventData === "{}") continue;

        try {
          const payload = JSON.parse(eventData);

          switch (eventType) {
            case "token":
              store.appendTokenToLastAssistantMessage(payload.text);
              break;
            case "sub_agent_token":
              store.appendSubAgentToken(payload.agent_name, payload.text);
              break;
            case "orchestration":
              store.setAgentState(`CEO delegating to ${payload.target_agent}...`);
              break;
            case "task_update":
              store.updateScratchpad({
                step: payload.step,
                status: payload.status,
                notes: payload.notes,
              });
              break;
            case "tool_call":
              store.updateToolStatus({
                tool_name: payload.tool_name,
                status: payload.status,
              });
              break;
            default:
              console.warn("Unknown event type:", eventType);
          }
        } catch (e) {
          console.error("Failed to parse event data", e, eventData);
        }
      }
    }
  } catch (error: any) {
    if (error.name === "AbortError") {
      console.log("Stream aborted");
      store.resetStreamState();
    } else {
      console.warn("Real connection failed. Falling back to simulation mode.", error);
      await runSimulatedChatStream(prompt, signal, assistantMessageId);
    }
  }
}
