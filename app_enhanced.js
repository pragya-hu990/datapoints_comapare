// Enhanced Application Logic for ReBIT vs FinFactor Comparison

let comparisonData = null;
let currentFilters = {
    fiType: 'all',
    category: 'all',
    search: '',
    matchType: 'all'
};

// Load data on page load
document.addEventListener('DOMContentLoaded', () => {
    loadData();
});

async function loadData() {
    try {
        const response = await fetch('comparison_data_enhanced.json');
        if (!response.ok) {
            throw new Error('Failed to load comparison data');
        }
        comparisonData = await response.json();
        initializeUI();
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('comparisonContent').innerHTML = `
            <div class="error" style="background: #fee2e2; color: #dc2626; padding: 2rem; border-radius: 1rem; text-align: center;">
                <h3>Error loading data</h3>
                <p>${error.message}</p>
                <p>Please ensure comparison_data_enhanced.json exists in the same directory.</p>
            </div>
        `;
    }
}

function initializeUI() {
    populateFilters();
    renderMetrics();
    renderCharts();
    renderInsights();
    renderComparison();
}

function populateFilters() {
    const fiTypeFilter = document.getElementById('fiTypeFilter');
    const fiTypes = Object.keys(comparisonData.comparison || {}).sort();
    
    fiTypes.forEach(fiType => {
        const summary = comparisonData.summary[fiType];
        if (summary && (summary.total_rebit > 0 || summary.total_finn > 0)) {
            const option = document.createElement('option');
            option.value = fiType;
            const displayName = fiType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            option.textContent = `${displayName}`;
            if (summary.total_finn > 0) {
                option.textContent += ` ⭐ (${summary.total_finn} FinFactor fields)`;
            }
            fiTypeFilter.appendChild(option);
        }
    });
    
    // Set default to first FI type with FinFactor data
    const withFinnData = fiTypes.find(ft => {
        const summary = comparisonData.summary[ft];
        return summary && summary.total_finn > 0;
    });
    
    if (withFinnData) {
        currentFilters.fiType = withFinnData;
        fiTypeFilter.value = withFinnData;
    }
}

function renderMetrics() {
    const metricsGrid = document.getElementById('metricsGrid');
    
    // Calculate overall metrics
    let totalRebit = 0;
    let totalFinn = 0;
    let totalCommon = 0;
    let totalSemanticMatches = 0;
    let fiTypesWithFinn = 0;
    
    Object.values(comparisonData.summary || {}).forEach(summary => {
        totalRebit += summary.total_rebit || 0;
        totalFinn += summary.total_finn || 0;
        totalCommon += summary.total_common || 0;
        totalSemanticMatches += summary.semantic_matches || 0;
        if (summary.total_finn > 0) fiTypesWithFinn++;
    });
    
    const metrics = [
        {
            label: 'Total ReBIT Fields',
            value: totalRebit.toLocaleString(),
            subtitle: 'Across all FI types',
            type: 'primary'
        },
        {
            label: 'Total FinFactor Fields',
            value: totalFinn.toLocaleString(),
            subtitle: `${fiTypesWithFinn} FI types covered`,
            type: 'warning'
        },
        {
            label: 'Common Fields',
            value: totalCommon.toLocaleString(),
            subtitle: `${((totalCommon / totalRebit) * 100).toFixed(1)}% coverage`,
            type: 'success'
        },
        {
            label: 'Semantic Matches',
            value: totalSemanticMatches.toLocaleString(),
            subtitle: 'Different names, same meaning 🎯',
            type: 'info'
        }
    ];
    
    metricsGrid.innerHTML = metrics.map(metric => `
        <div class="metric-card ${metric.type}">
            <div class="metric-label">${metric.label}</div>
            <div class="metric-value">${metric.value}</div>
            <div class="metric-subtitle">${metric.subtitle}</div>
        </div>
    `).join('');
}

function renderCharts() {
    renderCoverageChart();
    renderDistributionChart();
}

function renderCoverageChart() {
    const ctx = document.getElementById('coverageChart');
    if (!ctx) return;
    
    // Get FI types with FinFactor data
    const fiTypesWithData = Object.entries(comparisonData.summary || {})
        .filter(([_, summary]) => summary.total_finn > 0)
        .slice(0, 6); // Top 6
    
    const labels = fiTypesWithData.map(([fiType, _]) => 
        fiType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    );
    
    const rebitData = fiTypesWithData.map(([_, summary]) => summary.total_rebit);
    const finnData = fiTypesWithData.map(([_, summary]) => summary.total_finn);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'ReBIT Fields',
                    data: rebitData,
                    backgroundColor: 'rgba(37, 99, 235, 0.7)',
                    borderColor: 'rgba(37, 99, 235, 1)',
                    borderWidth: 2
                },
                {
                    label: 'FinFactor Fields',
                    data: finnData,
                    backgroundColor: 'rgba(245, 158, 11, 0.7)',
                    borderColor: 'rgba(245, 158, 11, 1)',
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    }
                },
                title: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        font: {
                            size: 12
                        }
                    }
                },
                x: {
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                }
            }
        }
    });
}

function renderDistributionChart() {
    const ctx = document.getElementById('distributionChart');
    if (!ctx) return;
    
    // Calculate totals
    let totalCommon = 0;
    let totalRebitOnly = 0;
    let totalFinnOnly = 0;
    
    Object.values(comparisonData.summary || {}).forEach(summary => {
        totalCommon += summary.total_common || 0;
        totalRebitOnly += summary.total_rebit_only || 0;
        totalFinnOnly += summary.total_finn_only || 0;
    });
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Common Fields', 'ReBIT Only', 'FinFactor Extra ⭐'],
            datasets: [{
                data: [totalCommon, totalRebitOnly, totalFinnOnly],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(37, 99, 235, 0.8)',
                    'rgba(245, 158, 11, 0.8)'
                ],
                borderColor: [
                    'rgba(16, 185, 129, 1)',
                    'rgba(37, 99, 235, 1)',
                    'rgba(245, 158, 11, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: {
                            size: 13,
                            weight: 'bold'
                        },
                        padding: 15
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value.toLocaleString()} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderInsights() {
    const insightsGrid = document.getElementById('insightsGrid');
    
    // Calculate insights
    const insights = [];
    
    // Find FI type with most FinFactor extra fields
    let maxFinnExtra = { fiType: '', count: 0 };
    let maxSemanticMatches = { fiType: '', count: 0 };
    
    Object.entries(comparisonData.summary || {}).forEach(([fiType, summary]) => {
        if (summary.total_finn_only > maxFinnExtra.count) {
            maxFinnExtra = { fiType, count: summary.total_finn_only };
        }
        if ((summary.semantic_matches || 0) > maxSemanticMatches.count) {
            maxSemanticMatches = { fiType, count: summary.semantic_matches || 0 };
        }
    });
    
    if (maxFinnExtra.count > 0) {
        insights.push({
            type: 'positive',
            title: 'Highest Value Addition',
            text: `<span class="insight-number">${maxFinnExtra.count}</span> extra fields in <strong>${maxFinnExtra.fiType.replace(/_/g, ' ')}</strong> - FinFactor provides significant additional data beyond ReBIT standard.`
        });
    }
    
    if (maxSemanticMatches.count > 0) {
        insights.push({
            type: 'info',
            title: 'Semantic Matching Success',
            text: `<span class="insight-number">${maxSemanticMatches.count}</span> semantic matches found in <strong>${maxSemanticMatches.fiType.replace(/_/g, ' ')}</strong> - Fields with different names but same meaning were intelligently matched.`
        });
    }
    
    // Coverage insight
    const totalRebit = Object.values(comparisonData.summary || {}).reduce((sum, s) => sum + (s.total_rebit || 0), 0);
    const totalCommon = Object.values(comparisonData.summary || {}).reduce((sum, s) => sum + (s.total_common || 0), 0);
    const coveragePercent = ((totalCommon / totalRebit) * 100).toFixed(1);
    
    insights.push({
        type: 'warning',
        title: 'Overall Coverage',
        text: `FinFactor covers <span class="insight-number">${coveragePercent}%</span> of ReBIT standard fields across all FI types, with substantial additional data points for enhanced analytics.`
    });
    
    insightsGrid.innerHTML = insights.map(insight => `
        <div class="insight-card ${insight.type}">
            <div class="insight-title">${insight.title}</div>
            <div class="insight-text">${insight.text}</div>
        </div>
    `).join('');
}

function renderComparison() {
    const comparisonContent = document.getElementById('comparisonContent');
    
    const fiType = currentFilters.fiType;
    
    if (fiType === 'all') {
        // Show all FI types
        const allFiTypes = Object.keys(comparisonData.comparison || {})
            .filter(ft => {
                const summary = comparisonData.summary[ft];
                return summary && (summary.total_rebit > 0 || summary.total_finn > 0);
            })
            .sort();
        
        comparisonContent.innerHTML = allFiTypes.map(ft => renderFiTypeSection(ft)).join('');
    } else {
        // Show specific FI type
        comparisonContent.innerHTML = renderFiTypeSection(fiType);
    }
}

function renderFiTypeSection(fiType) {
    const comparison = comparisonData.comparison[fiType];
    const summary = comparisonData.summary[fiType];
    
    if (!comparison || !summary) return '';
    
    const displayName = fiType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    
    // Filter fields based on current filters
    const commonFields = filterFields(comparison.common || [], 'common');
    const rebitOnlyFields = filterFields(comparison.rebit_only || [], 'rebit_only');
    const finnOnlyFields = filterFields(comparison.finn_only || [], 'finn_only');
    
    return `
        <div class="fi-type-section">
            <div class="fi-type-header">
                <h3 class="fi-type-title">${displayName}</h3>
                <div class="fi-type-stats">
                    <span class="stat-badge">ReBIT: ${summary.total_rebit}</span>
                    <span class="stat-badge">FinFactor: ${summary.total_finn}</span>
                    <span class="stat-badge">Common: ${summary.total_common}</span>
                    ${summary.semantic_matches > 0 ? `<span class="stat-badge">🎯 Semantic: ${summary.semantic_matches}</span>` : ''}
                </div>
            </div>
            <div class="comparison-grid">
                <div class="comparison-column">
                    <div class="column-header common">
                        <span>✓</span>
                        Common Fields (${commonFields.length})
                    </div>
                    ${renderCommonFields(commonFields)}
                </div>
                <div class="comparison-column">
                    <div class="column-header rebit-only">
                        <span>📋</span>
                        ReBIT Only (${rebitOnlyFields.length})
                    </div>
                    ${renderRebitOnlyFields(rebitOnlyFields)}
                </div>
                <div class="comparison-column">
                    <div class="column-header finn-only">
                        <span>⭐</span>
                        FinFactor Extra (${finnOnlyFields.length})
                    </div>
                    ${renderFinnOnlyFields(finnOnlyFields)}
                </div>
            </div>
        </div>
    `;
}

function filterFields(fields, category) {
    return fields.filter(field => {
        // Category filter
        if (currentFilters.category !== 'all' && currentFilters.category !== category) {
            return false;
        }
        
        // Match type filter
        if (currentFilters.matchType !== 'all' && category === 'common') {
            if (currentFilters.matchType === 'exact' && field.is_semantic_match) {
                return false;
            }
            if (currentFilters.matchType === 'semantic' && !field.is_semantic_match) {
                return false;
            }
        }
        
        // Search filter
        if (currentFilters.search) {
            const searchLower = currentFilters.search.toLowerCase();
            const fieldName = (field.name || field.canonical_name || field.rebit_name || field.finn_name || '').toLowerCase();
            return fieldName.includes(searchLower);
        }
        
        return true;
    });
}

function renderCommonFields(fields) {
    if (fields.length === 0) {
        return '<div class="empty-state">No common fields found</div>';
    }
    
    return fields.map(field => {
        const isSemanticMatch = field.is_semantic_match;
        return `
            <div class="field-item common ${isSemanticMatch ? 'semantic-match' : ''}">
                <div class="field-name">
                    ${field.canonical_name}
                    ${isSemanticMatch ? '<span class="field-badge semantic">🎯 Semantic Match</span>' : ''}
                </div>
                ${isSemanticMatch ? `
                    <div class="field-meta">
                        <span class="field-badge type">ReBIT: ${field.rebit_name}</span>
                        <span class="field-badge type">FinFactor: ${field.finn_name}</span>
                    </div>
                ` : ''}
                <div class="field-meta">
                    <span class="field-badge type">${field.rebit_field?.type || 'string'}</span>
                    ${field.rebit_field?.required ? '<span class="field-badge required">Required</span>' : '<span class="field-badge optional">Optional</span>'}
                </div>
                ${field.finn_field?.api_name ? `
                    <div class="api-info">
                        📡 ${field.finn_field.api_method || 'GET'} ${field.finn_field.api_path || field.finn_field.api_name}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

function renderRebitOnlyFields(fields) {
    if (fields.length === 0) {
        return '<div class="empty-state">No ReBIT-only fields</div>';
    }
    
    return fields.map(field => `
        <div class="field-item rebit-only">
            <div class="field-name">${field.name}</div>
            <div class="field-meta">
                <span class="field-badge type">${field.type || 'string'}</span>
                ${field.required ? '<span class="field-badge required">Required</span>' : '<span class="field-badge optional">Optional</span>'}
            </div>
            ${field.documentation ? `<div class="field-source">${field.documentation}</div>` : ''}
            ${field.source_schema ? `<div class="field-source">Schema: ${field.source_schema}</div>` : ''}
        </div>
    `).join('');
}

function renderFinnOnlyFields(fields) {
    if (fields.length === 0) {
        return '<div class="empty-state">No FinFactor extra fields</div>';
    }
    
    return fields.map(field => `
        <div class="field-item finn-only">
            <div class="field-name">⭐ ${field.name}</div>
            <div class="field-meta">
                <span class="field-badge type">${field.type || 'string'}</span>
            </div>
            ${field.api_name ? `
                <div class="api-info">
                    📡 ${field.api_method || 'GET'} ${field.api_path || field.api_name}
                </div>
            ` : ''}
        </div>
    `).join('');
}

function applyFilters() {
    currentFilters.fiType = document.getElementById('fiTypeFilter').value;
    currentFilters.category = document.getElementById('categoryFilter').value;
    currentFilters.search = document.getElementById('searchField').value;
    currentFilters.matchType = document.getElementById('matchTypeFilter').value;
    
    renderComparison();
}

function toggleControls() {
    const content = document.getElementById('controlsContent');
    const icon = document.getElementById('toggleIcon');
    
    content.classList.toggle('collapsed');
    icon.classList.toggle('collapsed');
}

// Export functions
function exportToPDF() {
    alert('PDF export functionality will be implemented using jsPDF library. For now, please use your browser\'s Print to PDF feature (Ctrl/Cmd + P).');
    window.print();
}

function exportToExcel() {
    alert('Excel export functionality will be implemented using SheetJS library. Coming soon!');
}

function exportToJSON() {
    const dataStr = JSON.stringify(comparisonData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'rebit_vs_finfactor_comparison.json';
    link.click();
    URL.revokeObjectURL(url);
}
