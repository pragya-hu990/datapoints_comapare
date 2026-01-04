// Comprehensive Comparison Dashboard Application

let comparisonData = null;
let currentFiType = null;
let currentViewMode = 'all';
let currentSearch = '';

// Load data on page load
document.addEventListener('DOMContentLoaded', () => {
    loadComparisonData();
});

async function loadComparisonData() {
    try {
        const response = await fetch('comparison_100_percent.json');
        if (!response.ok) {
            throw new Error('Failed to load comparison data');
        }
        comparisonData = await response.json();
        initializeDashboard();
    } catch (error) {
        console.error('Error loading data:', error);
        document.body.innerHTML = `
            <div style="text-align: center; padding: 4rem; color: white;">
                <h2>Error Loading Data</h2>
                <p>${error.message}</p>
                <p>Please ensure comparison_all_43_apis.json exists in the same directory.</p>
            </div>
        `;
    }
}

function initializeDashboard() {
    renderSummary();
    populateFiTypeSelect();
}

function renderSummary() {
    const summaryCards = document.getElementById('summaryCards');
    const metadata = comparisonData.metadata;
    
    // Calculate totals
    let totalRebit = 0;
    let totalFinn = 0;
    let totalCommon = 0;
    let categoriesWithData = 0;
    
    Object.values(comparisonData.categories).forEach(category => {
        if (category.summary.apis_count > 0) {
            categoriesWithData++;
            totalRebit += category.summary.rebit_total;
            totalFinn += category.summary.finn_total;
            totalCommon += category.summary.common;
        }
    });
    
    const cards = [
        {
            label: 'Total APIs Parsed',
            value: metadata.total_apis_parsed,
            subtitle: `${categoriesWithData} categories with data`,
            class: 'primary'
        },
        {
            label: 'Total ReBIT Fields',
            value: totalRebit.toLocaleString(),
            subtitle: `Across ${metadata.total_rebit_fi_types} FI types`,
            class: 'primary'
        },
        {
            label: 'Total FinFactor Fields',
            value: totalFinn.toLocaleString(),
            subtitle: `From ${metadata.total_categories} categories`,
            class: 'warning'
        },
        {
            label: 'Common Fields',
            value: totalCommon.toLocaleString(),
            subtitle: `${((totalCommon / totalRebit) * 100).toFixed(1)}% coverage`,
            class: 'success'
        }
    ];
    
    summaryCards.innerHTML = cards.map(card => `
        <div class="summary-card ${card.class}">
            <div class="label">${card.label}</div>
            <div class="value">${card.value}</div>
            <div class="subtitle">${card.subtitle}</div>
        </div>
    `).join('');
}

function populateFiTypeSelect() {
    const select = document.getElementById('fiTypeSelect');
    
    // Get categories with data
    const categoriesWithData = Object.entries(comparisonData.categories)
        .filter(([_, data]) => data.summary.apis_count > 0 || data.summary.rebit_total > 0)
        .sort((a, b) => a[0].localeCompare(b[0]));
    
    categoriesWithData.forEach(([category, data]) => {
        const option = document.createElement('option');
        option.value = category;
        const displayName = category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        option.textContent = `${displayName} (${data.summary.apis_count} APIs, ${data.summary.finn_total} fields)`;
        select.appendChild(option);
    });
}

function loadFiTypeData() {
    const select = document.getElementById('fiTypeSelect');
    currentFiType = select.value;
    
    if (!currentFiType) {
        document.getElementById('fiTypeDetails').innerHTML = `
            <div class="placeholder">
                <p>👆 Select a Financial Instrument Type to view detailed comparison</p>
            </div>
        `;
        document.getElementById('comparisonContainer').innerHTML = '';
        return;
    }
    
    const fiData = comparisonData.categories[currentFiType];
    renderFiTypeDetails(fiData);
    renderComparison(fiData);
}

function renderFiTypeDetails(fiData) {
    const container = document.getElementById('fiTypeDetails');
    const displayName = currentFiType.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
    
    container.innerHTML = `
        <div class="fi-header">
            <h2>${displayName}</h2>
            <div class="fi-stats">
                <div class="stat-item primary">
                    <span class="label">ReBIT Fields</span>
                    <span class="value">${fiData.summary.rebit_total}</span>
                </div>
                <div class="stat-item warning">
                    <span class="label">FinFactor Fields</span>
                    <span class="value">${fiData.summary.finn_total}</span>
                </div>
                <div class="stat-item success">
                    <span class="label">Common Fields</span>
                    <span class="value">${fiData.summary.common} (${fiData.summary.coverage_percent}%)</span>
                </div>
                <div class="stat-item">
                    <span class="label">ReBIT Only</span>
                    <span class="value">${fiData.summary.rebit_only}</span>
                </div>
                <div class="stat-item">
                    <span class="label">FinFactor Extra</span>
                    <span class="value">${fiData.summary.finn_only} ⭐</span>
                </div>
            </div>
            ${fiData.apis && fiData.apis.length > 0 ? `
                <div class="api-list">
                    <h3>📡 APIs (${fiData.apis.length})</h3>
                    <div class="api-tags">
                        ${fiData.apis.map(api => `<span class="api-tag">${api}</span>`).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

function renderComparison(fiData) {
    const container = document.getElementById('comparisonContainer');
    
    // Filter based on view mode and search
    let commonFields = fiData.common_fields || [];
    let rebitOnlyFields = fiData.rebit_only_fields || [];
    let finnOnlyFields = fiData.finn_only_fields || [];
    
    // Apply search filter
    if (currentSearch) {
        const searchLower = currentSearch.toLowerCase();
        commonFields = commonFields.filter(f => f.field_name.toLowerCase().includes(searchLower));
        rebitOnlyFields = rebitOnlyFields.filter(f => f.name.toLowerCase().includes(searchLower));
        finnOnlyFields = finnOnlyFields.filter(f => f.field_name.toLowerCase().includes(searchLower));
    }
    
    let html = '';
    
    // Common Fields
    if ((currentViewMode === 'all' || currentViewMode === 'common') && commonFields.length > 0) {
        html += `
            <div class="section-divider">
                <h3>✓ Common Fields (${commonFields.length})</h3>
                <p>Fields present in both ReBIT and FinFactor</p>
            </div>
            <div class="comparison-table">
                <div class="table-header">
                    <h3>Common Fields</h3>
                    <div class="count">${commonFields.length} fields found in both systems</div>
                </div>
                <div class="table-content">
                    ${commonFields.map(field => renderCommonFieldRow(field)).join('')}
                </div>
            </div>
        `;
    }
    
    // ReBIT Only Fields
    if ((currentViewMode === 'all' || currentViewMode === 'rebit_only') && rebitOnlyFields.length > 0) {
        html += `
            <div class="section-divider">
                <h3>📋 ReBIT Only Fields (${rebitOnlyFields.length})</h3>
                <p>Fields in ReBIT standard but not in FinFactor</p>
            </div>
            <div class="comparison-table">
                <div class="table-header">
                    <h3>ReBIT Only Fields</h3>
                    <div class="count">${rebitOnlyFields.length} fields</div>
                </div>
                <div class="table-content">
                    ${rebitOnlyFields.map(field => renderRebitOnlyFieldRow(field)).join('')}
                </div>
            </div>
        `;
    }
    
    // FinFactor Only Fields
    if ((currentViewMode === 'all' || currentViewMode === 'finn_only') && finnOnlyFields.length > 0) {
        html += `
            <div class="section-divider">
                <h3>⭐ FinFactor Extra Fields (${finnOnlyFields.length})</h3>
                <p>Additional fields provided by FinFactor beyond ReBIT standard</p>
            </div>
            <div class="comparison-table">
                <div class="table-header">
                    <h3>FinFactor Extra Fields</h3>
                    <div class="count">${finnOnlyFields.length} extra fields</div>
                </div>
                <div class="table-content">
                    ${finnOnlyFields.map(field => renderFinnOnlyFieldRow(field)).join('')}
                </div>
            </div>
        `;
    }
    
    if (!html) {
        html = '<div class="empty-state"><p>No fields match the current filters</p></div>';
    }
    
    container.innerHTML = html;
}

function renderCommonFieldRow(field) {
    const rebit = field.rebit;
    const finn = field.finn;
    
    return `
        <div class="field-row">
            <div class="field-column rebit">
                <div class="field-name">${field.field_name}</div>
                <div class="field-meta">
                    <span class="field-badge type">${rebit.type}</span>
                    <span class="field-badge ${rebit.required ? 'required' : 'optional'}">
                        ${rebit.required ? 'Required' : 'Optional'}
                    </span>
                </div>
                ${rebit.documentation ? `<div class="field-source"><strong>Description:</strong> ${rebit.documentation}</div>` : ''}
                <div class="field-source">
                    <strong>Schema:</strong> ${rebit.schema_file}
                </div>
                <div class="field-path">${rebit.path}</div>
            </div>
            <div class="field-column finn">
                <div class="field-name">${field.field_name}</div>
                <div class="field-meta">
                    <span class="field-badge type">From ${finn.api_count} API${finn.api_count > 1 ? 's' : ''}</span>
                </div>
                <div class="api-sources">
                    <div class="label">Provided by:</div>
                    ${finn.api_names.map(api => `
                        <div class="api-source-item">
                            <div class="api-name">${api}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
}

function renderRebitOnlyFieldRow(field) {
    return `
        <div class="field-row">
            <div class="field-column rebit" style="border-right: none;">
                <div class="field-name">${field.name}</div>
                <div class="field-meta">
                    <span class="field-badge type">${field.type}</span>
                    <span class="field-badge ${field.required ? 'required' : 'optional'}">
                        ${field.required ? 'Required' : 'Optional'}
                    </span>
                </div>
                ${field.documentation ? `<div class="field-source"><strong>Description:</strong> ${field.documentation}</div>` : ''}
                <div class="field-source">
                    <strong>Schema:</strong> ${field.schema_file}
                </div>
                <div class="field-path">${field.path}</div>
            </div>
            <div class="field-column finn">
                <div class="empty-state" style="padding: 1rem;">
                    <p style="font-size: 0.875rem; color: #9ca3af;">Not provided by FinFactor</p>
                </div>
            </div>
        </div>
    `;
}

function renderFinnOnlyFieldRow(field) {
    return `
        <div class="field-row">
            <div class="field-column rebit">
                <div class="empty-state" style="padding: 1rem;">
                    <p style="font-size: 0.875rem; color: #9ca3af;">Not in ReBIT standard</p>
                </div>
            </div>
            <div class="field-column finn" style="border-right: none;">
                <div class="field-name">⭐ ${field.field_name}</div>
                <div class="field-meta">
                    <span class="field-badge type">From ${field.api_count} API${field.api_count > 1 ? 's' : ''}</span>
                </div>
                <div class="api-sources">
                    <div class="label">Provided by:</div>
                    ${field.api_names.map(api => `
                        <div class="api-source-item">
                            <div class="api-name">${api}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
}

function updateView() {
    currentViewMode = document.getElementById('viewMode').value;
    currentSearch = document.getElementById('searchField').value;
    
    if (currentFiType) {
        const fiData = comparisonData.categories[currentFiType];
        renderComparison(fiData);
    }
}
