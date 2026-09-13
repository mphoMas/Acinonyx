/**
 * Interactive School Fee & Sibling Discount Calculator
 * South African Schools Act (SASA Section 39) & LKP Governance
 */

document.addEventListener('DOMContentLoaded', () => {
  initFeeCalculator();
});

function initFeeCalculator() {
  const gradeSelect = document.getElementById('calc-grade');
  const siblingSelect = document.getElementById('calc-siblings');
  const planSelect = document.getElementById('calc-plan');
  const incomeInput = document.getElementById('calc-income');

  // Outputs
  const totalAnnualEl = document.getElementById('calc-total-annual');
  const monthlyInstallmentEl = document.getElementById('calc-monthly-installment');
  const siblingSavingsEl = document.getElementById('calc-sibling-savings');
  const planBreakdownEl = document.getElementById('calc-plan-breakdown');
  const exemptionBadgeEl = document.getElementById('calc-exemption-badge');
  const exemptionTextEl = document.getElementById('calc-exemption-text');

  if (!gradeSelect || !totalAnnualEl) return;

  // Base Fees (2026/2027 Academic Schedule)
  const BASE_FEES = {
    'gr-r': { annual: 15500, monthly: 1550, name: 'Grade R' },
    'gr-primary': { annual: 13500, monthly: 1350, name: 'Grades 1–7' }
  };

  function calculate() {
    const gradeKey = gradeSelect.value;
    const numChildren = parseInt(siblingSelect.value, 10) || 1;
    const plan = planSelect.value;
    const monthlyIncome = parseFloat(incomeInput?.value) || 0;

    const baseData = BASE_FEES[gradeKey] || BASE_FEES['gr-primary'];
    const baseAnnual = baseData.annual;

    // Sibling Discount Structure:
    // 1st Child: 100%
    // 2nd Child: 5% discount on 2nd child
    // 3rd Child: 10% discount on 3rd child
    // 4th+ Child: 15% discount on subsequent children
    let grossAnnual = 0;
    let totalDiscount = 0;

    for (let i = 1; i <= numChildren; i++) {
      let childBase = baseAnnual;
      let discountRate = 0;
      if (i === 2) discountRate = 0.05;
      else if (i === 3) discountRate = 0.10;
      else if (i >= 4) discountRate = 0.15;

      const discount = childBase * discountRate;
      grossAnnual += childBase;
      totalDiscount += discount;
    }

    let netAnnual = grossAnnual - totalDiscount;

    // Plan-specific discounts:
    let planDiscount = 0;
    let monthlyDebitOrder = 0;
    let planDescription = '';

    if (plan === 'annual') {
      // 5% additional early settlement discount if paid upfront
      planDiscount = netAnnual * 0.05;
      netAnnual -= planDiscount;
      totalDiscount += planDiscount;
      monthlyDebitOrder = 0;
      planDescription = 'Single payment due by 31 January 2026 (Includes 5% upfront settlement rebate of R' + Math.round(planDiscount).toLocaleString() + ')';
    } else if (plan === 'monthly') {
      monthlyDebitOrder = Math.round(netAnnual / 10);
      planDescription = '10 Equal debit order installments: R' + monthlyDebitOrder.toLocaleString() + ' per month (February – November)';
    } else if (plan === 'quarterly') {
      const termAmount = Math.round(netAnnual / 4);
      monthlyDebitOrder = Math.round(netAnnual / 10);
      planDescription = '4 Quarterly term installments: R' + termAmount.toLocaleString() + ' at the start of each academic term';
    }

    // Update UI elements
    totalAnnualEl.textContent = 'R ' + Math.round(netAnnual).toLocaleString();
    if (monthlyInstallmentEl) {
      if (plan === 'annual') {
        monthlyInstallmentEl.textContent = 'Upfront Settled';
      } else {
        monthlyInstallmentEl.textContent = 'R ' + monthlyDebitOrder.toLocaleString() + ' /mo';
      }
    }

    if (siblingSavingsEl) {
      siblingSavingsEl.textContent = 'R ' + Math.round(totalDiscount).toLocaleString();
    }

    if (planBreakdownEl) {
      planBreakdownEl.textContent = planDescription;
    }

    // SASA Section 39 Statutory Exemption Assessment:
    // South African National Formula:
    // E = F / (Combined Gross Annual Income)
    // If E > 10% -> 100% Full Exemption
    // If E between 3% and 10% -> Partial Exemption
    // If E < 3% -> No Exemption
    if (exemptionBadgeEl && exemptionTextEl && monthlyIncome > 0) {
      const annualGrossIncome = monthlyIncome * 12;
      const feeRatio = (grossAnnual / annualGrossIncome) * 100;

      if (feeRatio >= 10) {
        exemptionBadgeEl.textContent = 'Likely Eligible: 100% Full SASA Exemption';
        exemptionBadgeEl.className = 'status-badge status-success';
        exemptionTextEl.innerHTML = 'Based on SASA criteria (fees represent <strong>' + feeRatio.toFixed(1) + '%</strong> of income), your family qualifies to apply for a <strong>Full School Fee Exemption</strong>. Please request Annexure B from Ms. N. Zikhali or Ms. H. Ash (GDE Subsidies Officers).';
      } else if (feeRatio >= 3.5) {
        exemptionBadgeEl.textContent = 'Likely Eligible: Partial Fee Exemption';
        exemptionBadgeEl.className = 'status-badge status-warning';
        exemptionTextEl.innerHTML = 'Fees represent <strong>' + feeRatio.toFixed(1) + '%</strong> of gross income. You qualify to apply for a sliding-scale <strong>Partial Subsidy</strong>. Applications open in Term 1.';
      } else {
        exemptionBadgeEl.textContent = 'Standard Fee Bracket';
        exemptionBadgeEl.className = 'status-badge status-neutral';
        exemptionTextEl.innerHTML = 'Fees represent <strong>' + feeRatio.toFixed(1) + '%</strong> of income (below the 3.5% statutory threshold). Standard debit order schedule applies.';
      }
    } else if (exemptionBadgeEl && exemptionTextEl) {
      exemptionBadgeEl.textContent = 'Enter Monthly Income to Assess';
      exemptionBadgeEl.className = 'status-badge status-neutral';
      exemptionTextEl.textContent = 'Enter your household combined gross monthly income above to calculate statutory exemption eligibility under SASA Section 39.';
    }
  }

  // Event Listeners
  [gradeSelect, siblingSelect, planSelect, incomeInput].forEach(el => {
    if (el) {
      el.addEventListener('input', calculate);
      el.addEventListener('change', calculate);
    }
  });

  // Initial Run
  calculate();
}
