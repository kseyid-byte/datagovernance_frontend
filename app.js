let products = [];
let masterData = { domains: [], stages: [] };
let currentWorkflow = null;
let activeStageId = "";
let activeView = "overview";
let activeWorkflowRequestId = "";
let currentUser = {
  email: "",
  role: "requester",
  canAdmin: false,
  canDeleteMasterData: false,
  name: "Requester",
};
const tableFilters = {};
const stageDescriptions = {
  intake: "Capture request, requester, priority, scope, and expected date.",
  reuse_domain: "Check reuse and assign the accountable lead subdomain.",
  ownership: "Assign owner, source system, delivery lead, and Lynx PM.",
  requirements: "Confirm KPIs, definitions, grain, sources, CDEs, and DQ rules.",
  architecture_review: "Confirm design, security, and tooling are approved.",
  build_validate: "Track build status, testing, UAT, and validation evidence.",
  publish: "Confirm Alation documentation and release readiness.",
  operate: "Move into support, monitoring, and regular review.",
};
const masterCollections = [
  { key: "domains", label: "Domains", fields: [{ name: "name", label: "Name" }] },
  { key: "businessUnits", label: "Business units", fields: [{ name: "name", label: "Name" }] },
  { key: "productTypes", label: "Product types", fields: [{ name: "name", label: "Name" }] },
  { key: "platforms", label: "Platforms", fields: [{ name: "name", label: "Name" }] },
  { key: "priorities", label: "Priorities", fields: [{ name: "name", label: "Name" }] },
  { key: "statuses", label: "Statuses", fields: [{ name: "name", label: "Name" }] },
  {
    key: "subdomains",
    label: "Subdomains",
    fields: [
      { name: "name", label: "Name" },
      { name: "domainId", label: "Domain", type: "domain" },
    ],
  },
  { key: "sourceSystems", label: "Source systems", fields: [{ name: "name", label: "Name" }] },
  {
    key: "scopeOptions",
    label: "Regions",
    fields: [
      { name: "name", label: "Name" },
      { name: "type", label: "Type", type: "select", options: ["Global", "Region"] },
      { name: "parentId", label: "Parent region", type: "scope-parent" },
    ],
  },
  { key: "buildStatuses", label: "Build statuses", fields: [{ name: "name", label: "Name" }] },
  {
    key: "users",
    label: "Users and roles",
    fields: [
      { name: "name", label: "Display name" },
      { name: "email", label: "Email", type: "email" },
      {
        name: "roleKey",
        label: "Role",
        type: "select",
        options: ["requester", "admin", "data_domain_owner", "domain_delivery_lead", "lynx_pm"],
      },
    ],
  },
];

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

async function loadSession() {
  const response = await fetch("/api/session");
  if (!response.ok) throw new Error(`Session API returned ${response.status}`);
  currentUser = await response.json();
}

function setView(view) {
  if (["admin", "master-data"].includes(view) && !currentUser.canAdmin) {
    view = "overview";
  }
  activeView = view;
  const viewIds = {
    overview: "overviewView",
    "new-request": "newRequestView",
    admin: "adminView",
    "master-data": "masterDataView",
  };
  document.querySelectorAll(".view").forEach((element) => {
    element.classList.toggle("active", element.id === viewIds[view]);
  });
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  if (view === "admin") renderAdmin();
  if (view === "master-data") renderMasterData();
}

function filteredProducts() {
  const search = document.getElementById("searchInput")?.value.trim().toLowerCase() || "";
  return products.filter((product) => {
    const matchesStage = !activeStageId || product.stageId === activeStageId;
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
    ["in_review", "in_progress"].includes(p.statusId)
  ).length;
  document.getElementById("metricBlocked").textContent = products.filter((p) => p.statusId === "blocked").length;
  document.getElementById("metricLive").textContent = products.filter((p) =>
    ["publish", "operate"].includes(p.stageId)
  ).length;
}

function renderRail() {
  const rail = document.getElementById("processRail");
  rail.innerHTML = "";
  const stages = masterData.stages || [];
  const totalProducts = products.length || 0;

  stages.forEach((stage) => {
    const count = products.filter((product) => product.stageId === stage.id).length;
    const percent = totalProducts ? Math.round((count / totalProducts) * 100) : 0;
    const button = document.createElement("button");
    button.type = "button";
    button.className = `rail-card${stage.id === activeStageId ? " active" : ""}`;
    button.setAttribute("aria-pressed", stage.id === activeStageId ? "true" : "false");
    button.innerHTML = `
      <span class="rail-card-step">Stage ${stage.number}</span>
      <span class="rail-card-name">${escapeHtml(stage.name)}</span>
      <span class="rail-card-desc">${escapeHtml(stageDescriptions[stage.id] || "")}</span>
      <span class="rail-card-count">${count} product${count === 1 ? "" : "s"} / ${percent}%</span>
    `;
    button.addEventListener("click", () => {
      activeStageId = activeStageId === stage.id ? "" : stage.id;
      render();
    });
    rail.appendChild(button);
  });
}

function stageNumberById(stageId, stages = masterData.stages || []) {
  return stages.find((stage) => stage.id === stageId)?.number || 0;
}

function progressPercent(stageId, stages = masterData.stages || []) {
  if (!stageId || !stages.length) return 0;
  return Math.min(100, (stageNumberById(stageId, stages) / stages.length) * 100);
}

function renderTable() {
  const rows = document.getElementById("productRows");
  const visible = filteredProducts();
  rows.innerHTML = "";

  const activeStageName = stageNameById(activeStageId);
  document.getElementById("pipelineTitle").textContent = activeStageId ? `${activeStageName} products` : "Product pipeline";
  document.getElementById("pipelineSubtitle").textContent = activeStageId
    ? `${visible.length} product${visible.length === 1 ? "" : "s"} in this stage.`
    : "All captured products across the governance process.";
  if (!visible.length) {
    rows.innerHTML = `<tr><td colspan="8">No products match the current filters.</td></tr>`;
    return;
  }

  visible.forEach((product) => {
    const row = document.createElement("tr");
    row.className = currentUser.canAdmin ? "clickable-row" : "";
    if (currentUser.canAdmin) {
      row.tabIndex = 0;
      row.setAttribute("role", "button");
      row.setAttribute("aria-label", `Open admin workflow for ${product.title}`);
      row.addEventListener("click", () => openProductWorkflow(product.requestId));
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openProductWorkflow(product.requestId);
        }
      });
    }
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

async function openProductWorkflow(requestId) {
  if (!currentUser.canAdmin) return;
  activeWorkflowRequestId = requestId;
  setView("admin");
  renderAdminOptions();
  const select = document.getElementById("adminProductSelect");
  if (select) select.value = requestId;
  await loadWorkflow(requestId);
  scrollAdminToTop();
}

function scrollAdminToTop() {
  requestAnimationFrame(() => {
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    document.querySelector(".main")?.scrollTo?.(0, 0);
  });
}

function stageNameById(stageId) {
  return masterData.stages?.find((stage) => stage.id === stageId)?.name || "";
}

function render() {
  renderAccess();
  renderMetrics();
  renderRail();
  renderTable();
  renderAdminOptions();
  if (activeView === "master-data") renderMasterData();
}

function renderAccess() {
  document.getElementById("userRoleLabel").textContent = currentUser.canAdmin
    ? `${currentUser.name} | Admin | ${currentUser.email || "No email"}`
    : `${currentUser.name} | Requester | ${currentUser.email || "No email"}`;
  document.querySelectorAll(".admin-only").forEach((element) => {
    element.hidden = !currentUser.canAdmin;
  });
  if (!currentUser.canAdmin && ["admin", "master-data"].includes(activeView)) {
    setView("overview");
  }
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
  const requesterEmail = document.querySelector('input[name="requesterEmail"]');
  if (requesterEmail && currentUser.email && !currentUser.canAdmin) {
    requesterEmail.value = currentUser.email;
  }
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
  activeWorkflowRequestId = requestId;
  const response = await fetch(`/api/requests/${requestId}/workflow`);
  if (!response.ok) throw new Error(`Workflow API returned ${response.status}`);
  const workflow = await response.json();
  if (activeWorkflowRequestId !== requestId) return;
  currentWorkflow = workflow;
  renderWorkflow();
}

function renderWorkflow() {
  const product = currentWorkflow.request;
  document.getElementById("adminProductCard").innerHTML = `
    <strong>${escapeHtml(product.title)}</strong>
    <span>${escapeHtml(product.id)} | ${escapeHtml(product.domain)} | ${escapeHtml(product.businessUnit || "No BU")}</span>
    <span>${escapeHtml(product.type)} | ${escapeHtml(product.platform)} | ${escapeHtml(product.priority)}</span>
    <span>Requester: ${escapeHtml(product.requester)} (${escapeHtml(product.requesterEmail)})</span>
    <span>Initiative: ${escapeHtml(product.initiative || "Not set")}</span>
    <span>Current stage: ${escapeHtml(product.stage)}</span>
    <label class="admin-status-field">
      Product status
      <select id="workflowStatusSelect">
        ${statusOptions(product.statusId)}
      </select>
    </label>
    <label class="admin-status-field">
      Status change reason
      <textarea id="workflowStatusReason" rows="3" placeholder="Reason for status change">${escapeHtml(product.statusChangeReason || "")}</textarea>
    </label>
    <button class="ghost-button full" id="saveWorkflowStatus" type="button">Save status</button>
    <span>${product.buildStatus ? `Build: ${escapeHtml(product.buildStatus)}` : "Build: Not set"}</span>
    <span>Scope: ${escapeHtml(product.scope || "Not set")}</span>
    <span>Expected date: ${escapeHtml(product.expectedDate || "Not set")}</span>
    <span>Delivery date: ${escapeHtml(product.deliveryDate || "Not set")}</span>
    <span>Delivery lead: ${escapeHtml(product.deliveryLead || "Not set")}</span>
    <span>Effort: ${escapeHtml(product.effort ?? "Not set")}</span>
    <span>Jira: ${product.jiraLink ? `<a href="${escapeHtml(product.jiraLink)}" target="_blank" rel="noreferrer">${escapeHtml(product.jiraEpicId || product.jiraLink)}</a>` : escapeHtml(product.jiraEpicId || "Not set")}</span>
    <span>Last status change: ${escapeHtml(product.lastStatusChangeDate || "Not set")} ${product.lastStatusChangedBy ? `by ${escapeHtml(product.lastStatusChangedBy)}` : ""}</span>
  `;

  const fields = document.getElementById("workflowFields");
  fields.innerHTML = "";
  fields.appendChild(renderWorkflowProgress());
  currentWorkflow.stages.forEach((stage) => {
    const form = document.createElement("form");
    form.className = `stage-panel${stage.isCurrent ? " current" : ""}${stage.complete ? " complete" : ""}${!stage.canSubmit ? " locked" : ""}`;
    form.id = `stagePanel-${stage.stageId}`;
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
    wireDomainSubdomainControls(form);
    form.addEventListener("submit", handleWorkflowSubmit);
    fields.appendChild(form);
  });

  renderTimeline();
  document.getElementById("saveWorkflowStatus").addEventListener("click", handleStatusSave);
}

function renderWorkflowProgress() {
  const stages = currentWorkflow.stages || [];
  const wrapper = document.createElement("section");
  wrapper.className = "workflow-stage-rail";
  wrapper.setAttribute("aria-label", "Workflow stage navigation");
  stages.forEach((stage) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `workflow-stage-button${stage.complete ? " complete" : ""}${stage.isCurrent ? " current" : ""}${!stage.canSubmit ? " locked" : ""}`;
    button.setAttribute("aria-current", stage.isCurrent ? "step" : "false");
    button.innerHTML = `
      <span class="workflow-stage-indicator" aria-hidden="true"></span>
      <span>${escapeHtml(stage.name)}</span>
    `;
    button.addEventListener("click", () => scrollToWorkflowStage(stage.stageId));
    wrapper.appendChild(button);
  });
  return wrapper;
}

function scrollToWorkflowStage(stageId) {
  const panel = document.getElementById(`stagePanel-${stageId}`);
  if (!panel) return;
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
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
  const value = requirement.answer_value || "";

  wrapper.appendChild(document.createTextNode(requirement.label));
  const help = document.createElement("span");
  help.className = "help";
  help.textContent = requirement.help_text;

  if (requirement.input_type === "checkbox") {
    wrapper.textContent = "";
    const row = document.createElement("span");
    row.className = "checkbox-row";
    const input = document.createElement("input");
    input.name = requirement.requirement_id;
    input.type = "checkbox";
    input.value = "true";
    input.checked = value === "true";
    input.disabled = !canSubmit;
    const label = document.createElement("span");
    label.textContent = requirement.label;
    row.append(input, label);
    wrapper.append(row, help);
    return wrapper;
  }

  if (requirement.input_type === "select") {
    const options = optionsForRequirement(requirement);
    const select = document.createElement("select");
    select.name = requirement.requirement_id;
    select.dataset.requirementKey = requirement.requirement_key;
    select.dataset.masterDataType = requirement.master_data_type || "";
    select.disabled = !canSubmit;
    select.appendChild(new Option("Select...", ""));
    options.forEach((option) => {
      select.appendChild(new Option(option.name, option.id, false, option.id === value));
    });
    wrapper.append(help, select);
    return wrapper;
  }

  if (requirement.input_type === "date") {
    const input = document.createElement("input");
    input.name = requirement.requirement_id;
    input.type = "date";
    input.value = value;
    input.disabled = !canSubmit;
    wrapper.append(help, input);
    return wrapper;
  }

  if (["text", "number"].includes(requirement.input_type)) {
    const input = document.createElement("input");
    input.name = requirement.requirement_id;
    input.type = requirement.input_type;
    input.value = value;
    input.disabled = !canSubmit;
    if (requirement.input_type === "number") {
      input.min = "0";
      input.step = "1";
    }
    wrapper.append(help, input);
    return wrapper;
  }

  const textarea = document.createElement("textarea");
  textarea.name = requirement.requirement_id;
  textarea.rows = 3;
  textarea.value = value;
  textarea.disabled = !canSubmit;
  wrapper.append(help, textarea);
  return wrapper;
}

function optionsForRequirement(requirement) {
  const options = masterData[requirement.master_data_type] || [];
  if (requirement.master_data_type !== "subdomains") return options;
  const domainId = currentWorkflow?.request?.domainId || "commercial";
  return options.filter((option) => option.domainId === domainId);
}

function subdomainOptionsForDomain(domainId) {
  return (masterData.subdomains || []).filter((option) => option.domainId === domainId);
}

function resetSelectOptions(select, options, selectedValue = "") {
  select.innerHTML = "";
  select.appendChild(new Option("Select...", ""));
  options.forEach((option) => {
    select.appendChild(new Option(option.name, option.id, false, option.id === selectedValue));
  });
  if (selectedValue && [...select.options].some((option) => option.value === selectedValue)) {
    select.value = selectedValue;
  }
}

function wireDomainSubdomainControls(form) {
  const domainSelect = form.querySelector('select[data-requirement-key="lead_domain_id"]');
  const subdomainSelect = form.querySelector('select[data-requirement-key="lead_subdomain_id"]');
  if (!domainSelect || !subdomainSelect) return;

  const refreshSubdomains = () => {
    const selectedValue = subdomainSelect.value;
    const options = subdomainOptionsForDomain(domainSelect.value || "commercial");
    const keepValue = options.some((option) => option.id === selectedValue) ? selectedValue : "";
    resetSelectOptions(subdomainSelect, options, keepValue);
  };

  domainSelect.addEventListener("change", refreshSubdomains);
  refreshSubdomains();
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
  try {
    const response = await fetch(`/api/requests/${currentWorkflow.request.requestId}/answers`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-Email": currentUser.email },
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
  } catch (error) {
    console.error("Failed to save workflow", error);
    document.getElementById("workflowMessage").textContent = error.message || "Workflow could not be saved.";
  }
}

async function handleStatusSave() {
  if (!currentWorkflow) return;
  const statusId = document.getElementById("workflowStatusSelect")?.value || "";
  const statusChangeReason = document.getElementById("workflowStatusReason")?.value || "";
  try {
    const response = await fetch(`/api/requests/${currentWorkflow.request.requestId}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-Email": currentUser.email },
      body: JSON.stringify({ statusId, statusChangeReason, updatedBy: currentUser.email || "admin" }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `Save status failed with ${response.status}`);
    }
    currentWorkflow = await response.json();
    document.getElementById("workflowMessage").textContent = "Status saved.";
    await loadProducts();
    render();
    renderWorkflow();
  } catch (error) {
    console.error("Failed to save status", error);
    document.getElementById("workflowMessage").textContent = error.message || "Status could not be saved.";
  }
}

function statusOptions(selectedId) {
  return (masterData.statuses || [])
    .map(
      (status) =>
        `<option value="${escapeHtml(status.id)}" ${status.id === selectedId ? "selected" : ""}>${escapeHtml(status.name)}</option>`
    )
    .join("");
}

function renderMasterData() {
  if (!currentUser.canAdmin) return;
  populateMasterDataCollectionSelect();
  renderMasterDataInputs();
  renderMasterDataList();
}

function populateMasterDataCollectionSelect() {
  const select = document.getElementById("masterDataCollection");
  if (!select || select.options.length) return;
  masterCollections.forEach((collection) => {
    select.appendChild(new Option(collection.label, collection.key));
  });
}

function selectedMasterCollection() {
  const key = document.getElementById("masterDataCollection")?.value || masterCollections[0].key;
  return masterCollections.find((collection) => collection.key === key) || masterCollections[0];
}

function renderMasterDataInputs() {
  const container = document.getElementById("masterDataInputs");
  if (!container) return;
  const collection = selectedMasterCollection();
  container.innerHTML = "";
  collection.fields.forEach((field) => {
    const label = document.createElement("label");
    label.textContent = field.label;
    let control;
    if (field.type === "select") {
      control = document.createElement("select");
      field.options.forEach((option) => control.appendChild(new Option(option, option)));
    } else if (field.type === "domain") {
      control = document.createElement("select");
      (masterData.domains || []).forEach((item) => control.appendChild(new Option(item.name, item.id)));
    } else if (field.type === "scope-parent") {
      control = document.createElement("select");
      control.appendChild(new Option("None", ""));
      (masterData.scopeOptions || [])
        .filter((item) => item.type === "Region")
        .forEach((item) => control.appendChild(new Option(item.name, item.id)));
    } else {
      control = document.createElement("input");
      control.type = field.type || "text";
      if (field.type === "email") control.placeholder = "name@syngenta.com";
    }
    control.name = field.name;
    control.required = field.name !== "parentId";
    label.appendChild(control);
    container.appendChild(label);
  });
}

function renderMasterDataList() {
  const list = document.getElementById("masterDataList");
  if (!list) return;
  const collection = selectedMasterCollection();
  const items = masterData[collection.key] || [];
  document.getElementById("masterDataTitle").textContent = collection.label;
  document.getElementById("masterDataSubtitle").textContent = `${items.length} value${items.length === 1 ? "" : "s"} configured.`;
  list.innerHTML = "";
  if (!items.length) {
    list.innerHTML = "<p>No values configured.</p>";
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("article");
    row.className = "master-data-item";
    const detail = [
      item.domainName ? `Domain: ${item.domainName}` : "",
      item.email,
      item.role_key || item.roleKey,
      item.type,
      item.parentId ? `Parent: ${scopeParentName(item.parentId)}` : "",
    ]
      .filter(Boolean)
      .join(" | ");
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(item.name)}</strong>
        <span>${escapeHtml(item.id)}${detail ? ` | ${escapeHtml(detail)}` : ""}</span>
      </div>
      ${currentUser.canDeleteMasterData ? `<button class="ghost-button" type="button">Remove</button>` : ""}
    `;
    if (currentUser.canDeleteMasterData) {
      row.querySelector("button").addEventListener("click", () => deleteMasterDataItem(collection.key, item.id));
    }
    list.appendChild(row);
  });
}

async function handleMasterDataSubmit(event) {
  event.preventDefault();
  const formEl = event.currentTarget;
  const collection = selectedMasterCollection();
  const form = new FormData(formEl);
  const payload = {};
  collection.fields.forEach((field) => {
    payload[field.name] = form.get(field.name) || "";
  });
  try {
    const response = await fetch(`/api/master-data/${collection.key}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-Email": currentUser.email },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `Save failed with ${response.status}`);
    masterData = result.masterData;
    formEl.reset();
    renderMasterData();
    populateRequestSelects();
    document.getElementById("masterDataMessage").textContent = "Saved.";
  } catch (error) {
    document.getElementById("masterDataMessage").textContent = error.message || "Save failed.";
  }
}

async function deleteMasterDataItem(collection, id) {
  try {
    const response = await fetch(`/api/master-data/${collection}/${encodeURIComponent(id)}`, {
      method: "DELETE",
      headers: { "X-User-Email": currentUser.email },
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `Delete failed with ${response.status}`);
    masterData = result.masterData;
    renderMasterData();
    populateRequestSelects();
    document.getElementById("masterDataMessage").textContent = "Removed.";
  } catch (error) {
    document.getElementById("masterDataMessage").textContent = error.message || "Remove failed.";
  }
}

async function handleSubmit(event) {
  event.preventDefault();
  const formElement = event.currentTarget;
  const form = new FormData(formElement);
  const payload = {
    title: form.get("title"),
    domain: form.get("domain"),
    businessUnit: form.get("businessUnit"),
    initiative: form.get("initiative"),
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
    activeStageId = "intake";
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
  activeStageId = "";
  render();
});

document.getElementById("sidebarToggle").addEventListener("click", () => {
  const collapsed = document.querySelector(".app-shell").classList.toggle("sidebar-collapsed");
  document.getElementById("sidebarToggle").textContent = collapsed ? "›" : "‹";
  document.getElementById("sidebarToggle").setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
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
document.getElementById("masterDataCollection").addEventListener("change", renderMasterData);
document.getElementById("masterDataForm").addEventListener("submit", handleMasterDataSubmit);

Promise.resolve()
  .then(loadSession)
  .then(() => Promise.all([loadMasterData(), loadProducts()]))
  .then(() => {
    populateRequestSelects();
    render();
  })
  .catch((error) => {
    console.error("App failed to load", error);
    alert("The local server is not responding. Start it with: python3 server.py 8502");
  });
