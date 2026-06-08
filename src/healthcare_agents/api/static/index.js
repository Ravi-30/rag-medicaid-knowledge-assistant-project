// Medicaid Agentic AI Dashboard Logic

document.addEventListener('DOMContentLoaded', () => {
    // State management
    const state = {
        role: 'provider',
        apiKey: 'provider-demo-key',
        activeTab: 'chat',
        lastCaseId: null,
        hitlPollingInterval: null,
        checkpoints: [],
        handoffs: []
    };

    // Role mapping configuration
    const roleKeys = {
        'provider': { key: 'provider-demo-key', label: 'X-API-Key: provider-demo-key (provider-101)' },
        'member': { key: 'member-demo-key', label: 'X-API-Key: member-demo-key (member-001)' },
        'ops_analyst': { key: 'ops-demo-key', label: 'X-API-Key: ops-demo-key (ops-analyst)' },
        'admin': { key: 'ops-demo-key', label: 'X-API-Key: ops-demo-key (ops-analyst / admin)' }
    };

    // DOM Elements
    const elements = {
        roleSelect: document.getElementById('user-role'),
        apiKeyDisplay: document.getElementById('api-key-display'),
        navItems: document.querySelectorAll('.nav-item'),
        tabPanels: document.querySelectorAll('.tab-panel'),
        chatForm: document.getElementById('chat-form'),
        chatInput: document.getElementById('chat-input'),
        chatMessages: document.getElementById('chat-messages-container'),
        scenarioButtons: document.querySelectorAll('.scenario-btn'),
        traceEngine: document.getElementById('trace-engine'),
        traceAgent: document.getElementById('trace-agent'),
        traceCase: document.getElementById('trace-case'),
        hitlBadge: document.getElementById('hitl-badge'),
        checkpointsList: document.getElementById('checkpoints-list'),
        handoffsList: document.getElementById('handoffs-list'),
        timelineNodes: document.querySelectorAll('.trace-step-node')
    };

    // 1. Navigation Handling
    elements.navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');
            switchTab(targetTab);
        });
    });

    function switchTab(tabId) {
        state.activeTab = tabId;
        
        elements.navItems.forEach(item => {
            if (item.getAttribute('data-tab') === tabId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        elements.tabPanels.forEach(panel => {
            if (panel.id === `panel-${tabId}`) {
                panel.classList.add('active');
            } else {
                panel.classList.remove('active');
            }
        });

        // Trigger updates depending on tab
        if (tabId === 'hitl') {
            fetchHITLData();
        }
    }

    // 2. Role Selector Handling
    elements.roleSelect.addEventListener('change', (e) => {
        const selectedRole = e.target.value;
        state.role = selectedRole;
        state.apiKey = roleKeys[selectedRole].key;
        elements.apiKeyDisplay.textContent = roleKeys[selectedRole].label;
        
        // Reset trace highlights
        resetTimeline();
        
        // Append system notification message
        appendMessage('system', `✦`, `Role changed to: <strong>${selectedRole.replace('_', ' ')}</strong>. API header updated. New requests will execute with this profile's permissions.`);
    });

    // 3. Scenario suggestion handling
    elements.scenarioButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const queryText = btn.getAttribute('data-query');
            elements.chatInput.value = queryText;
            submitMessage(queryText);
        });
    });

    // 4. Chat Submission Handling
    elements.chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const queryText = elements.chatInput.value.trim();
        if (!queryText) return;
        elements.chatInput.value = '';
        submitMessage(queryText);
    });

    async function submitMessage(query) {
        // Append User Message
        appendMessage('user', 'U', query);
        
        // Set loading/pulsing states on trace sidebar
        resetTimeline();
        elements.traceAgent.textContent = 'Orchestrating...';
        elements.traceCase.textContent = '-';
        
        // Visual node transition indicator
        setTimelineNode('node-guard_input', 'active');
        
        try {
            // Determine API Key
            const headers = {
                'Content-Type': 'application/json',
                'X-API-Key': state.apiKey
            };

            // Call POST /v1/chat endpoint
            const response = await fetch('/v1/chat', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    query: query,
                    member_id: state.role === 'member' ? 'member-001' : null
                })
            });

            if (!response.ok) {
                const errDetail = await response.json();
                throw new Error(errDetail.detail || 'API request failed');
            }

            const data = await response.json();
            
            // Highlight steps completed
            animateTimeline(data);

            // Display result
            setTimeout(() => {
                appendAgentMessage(data);
                
                // Track case for updates
                if (data.metadata && data.metadata.case_id) {
                    state.lastCaseId = data.metadata.case_id;
                    elements.traceCase.textContent = data.metadata.case_id;
                }
                
                // If the response required HITL, trigger alert
                if (data.metadata && (data.metadata.blocked || data.metadata.status === 'escalated' || data.metadata.status === 'denied')) {
                    fetchHITLData();
                }
            }, 1000);

        } catch (error) {
            console.error('Error in agent chat:', error);
            setTimelineNode('node-guard_input', 'blocked');
            elements.traceAgent.textContent = 'Failed';
            appendMessage('system', '❌', `<strong>Error:</strong> ${error.message}`);
        }
    }

    // Timeline Animation based on API response
    function animateTimeline(apiResponse) {
        resetTimeline();
        
        const nodes = ['node-guard_input', 'node-triage', 'node-context_enrichment', 'node-select_agent', 'node-planning'];
        
        // Sequentially highlight reasoning phases
        let delay = 0;
        nodes.forEach(nodeId => {
            setTimeout(() => {
                setTimelineNode(nodeId, 'completed');
            }, delay);
            delay += 150;
        });

        // Check if blocked by policy
        setTimeout(() => {
            if (apiResponse.metadata && apiResponse.metadata.policy_blocked) {
                setTimelineNode('node-governed_decision', 'blocked');
                elements.traceAgent.textContent = 'Blocked by Policy';
                return;
            }
            setTimelineNode('node-governed_decision', 'completed');
        }, 800);

        // Highlight tools node if any tools used
        setTimeout(() => {
            const mcpUsed = apiResponse.mcp_tools_used && apiResponse.mcp_tools_used.length > 0;
            if (mcpUsed) {
                setTimelineNode('node-tool_execution', 'completed');
            }
        }, 950);

        // Reflection node
        setTimeout(() => {
            setTimelineNode('node-reflection', 'completed');
            elements.traceAgent.textContent = apiResponse.agent || 'Orchestrator';
        }, 1100);

        // Escalation / HITL Node
        setTimeout(() => {
            const hasHITL = apiResponse.metadata && (apiResponse.metadata.status === 'escalated' || apiResponse.metadata.status === 'denied' || apiResponse.metadata.blocked);
            if (hasHITL) {
                setTimelineNode('node-escalation', 'active');
            }
        }, 1250);

        // Response & Persist Build Completes
        setTimeout(() => {
            setTimelineNode('node-response', 'completed');
            setTimelineNode('node-persist', 'completed');
            setTimelineNode('node-action_complete', 'completed');
        }, 1400);
    }

    function resetTimeline() {
        elements.timelineNodes.forEach(node => {
            node.className = 'trace-step-node';
        });
    }

    function setTimelineNode(nodeId, statusClass) {
        const el = document.getElementById(nodeId);
        if (el) {
            el.className = `trace-step-node ${statusClass}`;
        }
    }

    // Message Appending Helpers
    function appendMessage(role, avatar, content) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        msgDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <p>${content}</p>
            </div>
        `;
        elements.chatMessages.appendChild(msgDiv);
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }

    function appendAgentMessage(apiResponse) {
        const content = apiResponse.content || "Workflow completed.";
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message system';
        
        let badgesHtml = '';
        if (apiResponse.agent) {
            badgesHtml += `<span class="meta-badge agent">Agent: ${apiResponse.agent}</span>`;
        }
        if (apiResponse.mcp_tools_used && apiResponse.mcp_tools_used.length > 0) {
            apiResponse.mcp_tools_used.forEach(tool => {
                badgesHtml += `<span class="meta-badge tool">Tool: ${tool}</span>`;
            });
        }
        if (apiResponse.metadata && apiResponse.metadata.role) {
            badgesHtml += `<span class="meta-badge role">Auth Role: ${apiResponse.metadata.role}</span>`;
        }

        msgDiv.innerHTML = `
            <div class="message-avatar">✦</div>
            <div class="message-content">
                <p>${content.replace(/\n/g, '<br>')}</p>
                <div class="message-metadata-badges">
                    ${badgesHtml}
                </div>
            </div>
        `;
        elements.chatMessages.appendChild(msgDiv);
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }

    // 5. Specialist HITL Actions & Polling
    async function fetchHITLData() {
        try {
            const headers = { 'X-API-Key': state.apiKey };
            
            // 1. Fetch checkpoints
            const resCP = await fetch('/v1/dashboard/checkpoints', { headers });
            if (resCP.ok) {
                state.checkpoints = await resCP.json();
            }

            // 2. Fetch handoffs
            const resHO = await fetch('/v1/dashboard/handoffs', { headers });
            if (resHO.ok) {
                state.handoffs = await resHO.json();
            }

            renderHITLLists();

        } catch (error) {
            console.error('Error fetching HITL data:', error);
        }
    }

    function renderHITLLists() {
        // Calculate pending count for badge
        const totalPending = state.checkpoints.length + state.handoffs.length;
        if (totalPending > 0) {
            elements.hitlBadge.textContent = totalPending;
            elements.hitlBadge.style.display = 'block';
        } else {
            elements.hitlBadge.style.display = 'none';
        }

        // Render Checkpoints
        elements.checkpointsList.innerHTML = '';
        if (state.checkpoints.length === 0) {
            elements.checkpointsList.innerHTML = '<div class="empty-state">No pending action checkpoints requiring approval.</div>';
        } else {
            state.checkpoints.forEach(cp => {
                const card = document.createElement('div');
                card.className = 'hitl-card';
                card.innerHTML = `
                    <div class="hitl-card-header">
                        <span class="hitl-id">Case Ref: ${cp.case_id}</span>
                        <span class="hitl-priority high">Needs Approval</span>
                    </div>
                    <div class="hitl-card-body">
                        <p><strong>Triggered Step:</strong> ${cp.step}</p>
                        <p><strong>Escalation Reason:</strong> ${cp.reason}</p>
                    </div>
                    <div class="hitl-actions">
                        <button class="hitl-btn approve" data-case-id="${cp.case_id}">Approve Action</button>
                    </div>
                `;
                elements.checkpointsList.appendChild(card);
            });

            // Bind click handlers to approve buttons
            elements.checkpointsList.querySelectorAll('.approve').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const caseId = btn.getAttribute('data-case-id');
                    await approveCheckpoint(caseId);
                });
            });
        }

        // Render Handoffs
        elements.handoffsList.innerHTML = '';
        if (state.handoffs.length === 0) {
            elements.handoffsList.innerHTML = '<div class="empty-state">No escalated handoffs currently in queue.</div>';
        } else {
            state.handoffs.forEach(ho => {
                const card = document.createElement('div');
                card.className = 'hitl-card';
                card.innerHTML = `
                    <div class="hitl-card-header">
                        <span class="hitl-id">Handoff: ${ho.escalation_id}</span>
                        <span class="hitl-priority normal">${ho.priority}</span>
                    </div>
                    <div class="hitl-card-body">
                        <p><strong>Case Reference:</strong> ${ho.case_id}</p>
                        <p><strong>Status:</strong> ${ho.status}</p>
                    </div>
                    <div class="hitl-actions">
                        <button class="hitl-btn ack" data-esc-id="${ho.escalation_id}">Acknowledge Handoff</button>
                    </div>
                `;
                elements.handoffsList.appendChild(card);
            });

            // Bind click handlers to acknowledge buttons
            elements.handoffsList.querySelectorAll('.ack').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const escId = btn.getAttribute('data-esc-id');
                    await acknowledgeHandoff(escId);
                });
            });
        }
    }

    async function approveCheckpoint(caseId) {
        try {
            const headers = { 'X-API-Key': state.apiKey };
            const response = await fetch(`/v1/dashboard/checkpoints/approve/${caseId}`, {
                method: 'POST',
                headers: headers
            });
            if (response.ok) {
                appendMessage('system', '✔', `Checkpoint approved successfully for case <strong>${caseId}</strong>.`);
                fetchHITLData();
            } else {
                const err = await response.json();
                alert(`Approval failed: ${err.detail}`);
            }
        } catch (err) {
            console.error(err);
        }
    }

    async function acknowledgeHandoff(escId) {
        try {
            const headers = { 'X-API-Key': state.apiKey };
            const response = await fetch(`/v1/dashboard/handoffs/acknowledge/${escId}`, {
                method: 'POST',
                headers: headers
            });
            if (response.ok) {
                appendMessage('system', '✔', `Handoff escalation <strong>${escId}</strong> acknowledged. Case assigned to Specialist.`);
                fetchHITLData();
            } else {
                const err = await response.json();
                alert(`Acknowledgment failed: ${err.detail}`);
            }
        } catch (err) {
            console.error(err);
        }
    }

    // Set up polling for Specialist HITL tasks
    state.hitlPollingInterval = setInterval(fetchHITLData, 5000);
});
