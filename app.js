let products = [];
let masterData = { domains: [], stages: [] };
let currentWorkflow = null;
let activeStage = "";
let activeView = "overview";
const tableFilters = {};

async function loadProducts() {
  const response = await fetch("/api/requests");
  if (!response.ok) throw new Error(`API returned ${response.status}`);
  products = await response.json();
}

async function loadMasterData() {
  const response = await fetch("/api/master-data");
  if (!response.ok) throw new Error(`API returned ${response.status}`);
  masterData = await response.json();
}

function setView(view) {
  activeView = view;
  const viewIds = {
    overview: "overviewView",
    "new-request": "newRequestView",
    admin: "adminView",
  };
  document.querySelectorAll(".view").forEach((element) => {
    element.classList.toggle("active", element.id === viewIds[view]);
  });
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  if (view === "admin") renderAdmin();
}

function stageNames() {
  return (masterData.stages || []).map((stage) => stage.name);
}

function filteredProducts() {
  const search = document.getElementById("searchInput")?.value.trim().toLowerCase() || "";
  return products.filter((product) => {
    const matchesStage = !activeStage || product.stage === activeStage;
    const haystack = [
      product.title,
      product.domain,
      product.businessUnit,
      product.owner,
      product.platform,
      product.priority,
      product.status,
    ]
      .join(" ")
      .toLowerCase();
    return matchesStage && (!search || haystack.includes(search)) && matchesColumnFilters(product);
  });
}

function matchesColumnFilters(product) {
  return Object.entries(tableFilters).every(([column, filter]) => {
    if (!filter) return true;
    const value = column === "daysInStage" ? String(product.daysInStage ?? "") : String(product[column] ?? "");
    return value.toLowerCase().includes(filter);
  });
}

function renderMetrics() {
  document.getElementById("metricTotal").textContent = products.length;
  document.getElementById("metricReview").textContent = products.filter((p) =>
    ["In review", "In progress"].includes(p.status)
  ).length;
  document.getElementById("metricBlocked").textContent = products.filter((p) => p.status === "Blocked").length;
  document.getElementById("metricLive").textContent = products.filter((p) =>
    ["Publish", "Operate"].includes(p.stage)
  ).length;
}

function renderRail() {
  const rail = document.getElementById("processRail");
  rail.innerHTML = "";

  stageNames().forEach((stage) => {
    const count = products.filter((product) => product.stage === stage).length;
    const button = document.createElement("button");
    button.type = "button";
    button.className = `rail-card${stage === activeStage ? " active" : ""}`;
    button.setAttribute("aria-pressed", stage === activeStage ? "true" : "false");
    button.innerHTML = `
      <span class="rail-card-name">${escapeHtml(stage)}</span>
      <span class="rail-card-count">${count} products</span>
    `;
    button.addEventListener("click", () => {
      activeStage = activeStage === stage ? "" : stage;
      render();
    });
    rail.appendChild(button);
  });
}

function renderTable() {
  const rows = document.getElementById("productRows");
  const visible = filteredProducts();
  rows.innerHTML = "";

  document.getElementById("pipelineTitle").textContent = activeStage ? `${activeStage} products` : "Product pipeline";
  document.getElementById("pipelineSubtitle").textContent = activeStage
    ? `${visible.length} product${visible.length === 1 ? "" : "s"} in this stage.`
    : "All captured products across the governance process.";
  document.getElementById("sidebarStage").textContent = activeStage || "All products";
  document.getElementById("sidebarCount").textContent = `${visible.length} visible`;

  if (!visible.length) {
    rows.innerHTML = `<tr><td colspan="8">No products match the current filters.</td></tr>`;
    return;
  }

  visible.forEach((product) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><strong>${escapeHtml(product.title)}</strong><br><small>${escapeHtml(product.id)}</small></td>
      <td>${escapeHtml(product.domain)}<br><small>${escapeHtml(product.businessUnit || "")}</small></td>
      <td>${escapeHtml(product.type)}</td>
      <td>${escapeHtml(product.platform)}</td>
      <td>${escapeHtml(product.stage)}</td>
      <td><strong>${escapeHtml(product.daysInStage ?? 0)}</strong><br><small>${escapeHtml(product.currentStageEnteredAt || "")}</small></td>
      <td><span class="status ${statusClass(product.status)}">${escapeHtml(product.status)}</span></td>
      <td>${escapeHtml(product.owner)}</td>
    `;
    rows.appendChild(row);
  });
}

function render() {
  renderMetrics();
  renderRail();
  renderTable();
  renderAdminOptions();
}

function populateSelect(id, options, selectedValue = "") {
  const select = document.getElementById(id);
  if (!select) return;
  select.innerHTML = "";
  (options || []).forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.parentId
      ? `${item.name} (${scopeParentName(item.parentId)})`
      : item.name;
    select.appendChild(option);
  });
  if (selectedValue) select.value = selectedValue;
}

function scopeParentName(parentId) {
  return masterData.scopeOptions?.find((item) => item.id === parentId)?.name || parentId;
}

function populateRequestSelects() {
  populateSelect("domainSelect", masterData.domains);
  populateSelect("businessUnitSelect", masterData.businessUnits);
  populateSelect("productTypeSelect", masterData.productTypes);
  populateSelect("platformSelect", masterData.platforms);
  populateSelect("prioritySelect", masterData.priorities, "p2");
  populateSelect("scopeSelect", masterData.scopeOptions);
}

function renderAdminOptions() {
  const select = document.getElementById("adminProductSelect");
  if (!select) return;
  const selected = select.value;
  select.innerHTML = "";
  products.forEach((product) => {
    const option = document.createElement("option");
    option.value = product.requestId;
    option.textContent = `${product.id} - ${product.title}`;
    select.appendChild(option);
  });
  if (selected && products.some((product) => product.requestId === selected)) {
    select.value = selected;
  }
}

async function renderAdmin() {
  renderAdminOptions();
  const select = document.getElementById("adminProductSelect");
  if (!select.value && products[0]) select.value = products[0].requestId;
  if (!select.value) {
    document.getElementById("adminProductCard").innerHTML = "No products available.";
    document.getElementById("workflowFields").innerHTML = "";
    document.getElementById("timelineList").innerHTML = "";
    return;
  }
  await loadWorkflow(select.value);
}

async function loadWorkflow(requestId) {
  const response = await fetch(`/api/requests/${requestId}/workflow`);
  if (!response.ok) throw new Error(`Workflow API returned ${response.status}`);
  currentWorkflow = await response.json();
  renderWorkflow();
}

function renderWorkflow() {
  const product = currentWorkflow.request;
  document.getElementById("adminProductCard").innerHTML = `
    <strong>${escapeHtml(product.title)}</strong>
    <span>${escapeHtml(product.id)} | ${escapeHtml(product.domain)} | ${escapeHtml(product.businessUnit || "No BU")}</span>
    <span>${escapeHtml(product.type)} | ${escapeHtml(product.platform)} | ${escapeHtml(product.priority)}</span>
    <span>Requester: ${escapeHtml(product.requester)} (${escapeHtml(product.requesterEmail)})</span>
    <span>Current stage: ${escapeHtml(product.stage)}</span>
    <label class="admin-status-field">
      Product status
      <select id="workflowStatusSelect">
        ${statusOptions(product.statusId)}
      </select>
    </label>
    <span>${product.buildStatus ? `Build: ${escapeHtml(product.buildStatus)}` : "Build: Not set"}</span>
    <span>Scope: ${escapeHtml(product.scope || "Not set")}</span>
    <span>Expected date: ${escapeHtml(product.expectedDate || "Not set")}</span>
  `;

  const fields = document.getElementById("workflowFields");
  fields.innerHTML = "";
  currentWorkflow.stages.forEach((stage) => {
    const form = document.createElement("form");
    form.className = `stage-panel${stage.isCurrent ? " current" : ""}${stage.complete ? " complete" : ""}${!stage.canSubmit ? " locked" : ""}`;
    form.dataset.stageId = stage.stageId;
    form.innerHTML = `
      <div class="stage-panel-header">
        <div>
          <strong>${stage.number}. ${escapeHtml(stage.name)}</strong>
          <span>${stageStatusText(stage)}</span>
        </div>
        <div class="stage-actions">
          <button class="primary-action" type="submit" ${stage.canSubmit ? "" : "disabled"}>Save stage</button>
        </div>
      </div>
      <div class="stage-field-grid"></div>
    `;
    const grid = form.querySelector(".stage-field-grid");
    stage.requirements.forEach((requirement) => {
      grid.appendChild(renderRequirement(requirement, stage.canSubmit));
    });
    form.addEventListener("submit", handleWorkflowSubmit);
    fields.appendChild(form);
  });

  renderTimeline();
}

function stageStatusText(stage) {
  if (!stage.canSubmit) return "Locked until previous stages are complete";
  if (stage.complete) return "Complete";
  if (stage.isCurrent) return "Current stage";
  return "Available";
}

function renderRequirement(requirement, canSubmit) {
  const wrapper = document.createElement("label");
  wrapper.className = `requirement-field ${requirement.input_type}`;
  const disabled = canSubmit ? "" : "disabled";
  const value = requirement.answer_value || "";

  if (requirement.input_type === "checkbox") {
    wrapper.innerHTML = `
      <span class="checkbox-row">
        <input name="${requirement.requirement_id}" type="checkbox" value="true" ${value === "true" ? "checked" : ""} ${disabled} />
        <span>${escapeHtml(requirement.label)}</span>
      </span>
      <span class="help">${escapeHtml(requirement.help_text)}</span>
    `;
    return wrapper;
  }

  if (requirement.input_type === "select") {
    const options = masterData[requirement.master_data_type] || [];
    wrapper.innerHTML = `
      ${escapeHtml(requirement.label)}
      <span class="help">${escapeHtml(requirement.help_text)}</span>
      <select name="${requirement.requirement_id}" ${disabled}>
        <option value="">Select...</option>
        ${options
          .map((option) => `<option value="${escapeHtml(option.id)}" ${option.id === value ? "selected" : ""}>${escapeHtml(option.name)}</option>`)
          .join("")}
      </select>
    `;
    return wrapper;
  }

  if (requirement.input_type === "date") {
    wrapper.innerHTML = `
      ${escapeHtml(requirement.label)}
      <span class="help">${escapeHtml(requirement.help_text)}</span>
      <input name="${requirement.requirement_id}" type="date" value="${escapeHtml(value)}" ${disabled} />
    `;
    return wrapper;
  }

  wrapper.innerHTML = `
    ${escapeHtml(requirement.label)}
    <span class="help">${escapeHtml(requirement.help_text)}</span>
    <textarea name="${requirement.requirement_id}" rows="3" ${disabled}>${escapeHtml(value)}</textarea>
  `;
  return wrapper;
}

function renderTimeline() {
  const list = document.getElementById("timelineList");
  list.innerHTML = "";
  (currentWorkflow.timeline || []).forEach((event) => {
    const item = document.createElement("article");
    item.className = "timeline-item";
    item.innerHTML = `
      <strong>${escapeHtml(event.event_label)}</strong>
      <span>${formatDate(event.created_at)} | ${escapeHtml(event.created_by || "system")}</span>
      <p>${escapeHtml(event.event_detail || "")}</p>
    `;
    list.appendChild(item);
  });
}

async function handleWorkflowSubmit(event) {
  event.preventDefault();
  if (!currentWorkflow) return;

  const form = event.currentTarget;
  const stageId = form.dataset.stageId;
  const stage = currentWorkflow.stages.find((item) => item.stageId === stageId);
  const data = new FormData(form);
  const answers = {};
  stage.requirements.forEach((requirement) => {
    if (requirement.input_type === "checkbox") {
      answers[requirement.requirement_id] = data.get(requirement.requirement_id) === "true";
    } else {
      answers[requirement.requirement_id] = data.get(requirement.requirement_id) || "";
    }
  });

  const status = document.getElementById("workflowStatusSelect")?.value || "";
  const response = await fetch(`/api/requests/${currentWorkflow.request.requestId}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stageId, answers, statusId: status, updatedBy: "admin" }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.error || `Save answers failed with ${response.status}`);
  }

  currentWorkflow = await response.json();
  document.getElementById("workflowMessage").textContent = currentWorkflow.advanced
    ? `Saved. Product advanced to ${currentWorkflow.request.stage}.`
    : "Saved. Complete required fields to advance.";
  await loadProducts();
  render();
  renderWorkflow();
}

function statusOptions(selectedId) {
  return (masterData.statuses || [])
    .map(
      (status) =>
        `<option value="${escapeHtml(status.id)}" ${status.id === selectedId ? "selected" : ""}>${escapeHtml(status.name)}</option>`
    )
    .join("");
}

async function handleSubmit(event) {
  event.preventDefault();
  const formElement = event.currentTarget;
  const form = new FormData(formElement);
  const payload = {
    title: form.get("title"),
    domain: form.get("domain"),
    businessUnit: form.get("businessUnit"),
    description: form.get("description"),
    productType: form.get("productType"),
    platform: form.get("platform"),
    priority: form.get("priority"),
    scope: form.get("scope"),
    requester: form.get("requester"),
    requesterEmail: form.get("requesterEmail"),
    expectedDate: form.get("expectedDate"),
    additionalComments: form.get("additionalComments"),
  };

  try {
    const response = await fetch("/api/requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `API returned ${response.status}`);
    }
    const created = await response.json();
    products = [created, ...products];
    formElement.reset();
    populateRequestSelects();
    activeStage = "Intake";
    setView("overview");
    render();
  } catch (error) {
    console.error("Failed to create request", error);
    alert(error.message || "Request could not be saved to the temporary database.");
  }
}

function statusClass(value) {
  return String(value || "").toLowerCase().replaceAll(" ", "-");
}

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view));
});

document.getElementById("clearStage").addEventListener("click", () => {
  activeStage = "";
  render();
});

document.getElementById("searchInput").addEventListener("input", renderTable);
document.querySelectorAll(".column-filter").forEach((input) => {
  input.addEventListener("input", (event) => {
    tableFilters[event.target.dataset.column] = event.target.value.trim().toLowerCase();
    renderTable();
  });
});
document.getElementById("requestForm").addEventListener("submit", handleSubmit);
document.getElementById("adminProductSelect").addEventListener("change", (event) => loadWorkflow(event.target.value));

Promise.all([loadMasterData(), loadProducts()])
  .then(() => {
    populateRequestSelects();
    render();
  })
  .catch((error) => {
    console.error("App failed to load", error);
    alert("The local server is not responding. Start it with: python3 server.py 8502");
  });
