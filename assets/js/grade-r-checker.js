/**
 * Grade R Intake Cohort & Age Eligibility Checker
 * SASA Admission Age Regulations & Direct Enrolment Guidance
 */

document.addEventListener('DOMContentLoaded', () => {
  initGradeRChecker();
});

function initGradeRChecker() {
  const birthYearSelect = document.getElementById('checker-birth-year');
  const birthMonthSelect = document.getElementById('checker-birth-month');
  const resultCard = document.getElementById('checker-result-card');
  const resultTitle = document.getElementById('checker-result-title');
  const resultBadge = document.getElementById('checker-result-badge');
  const resultExplanation = document.getElementById('checker-result-explanation');
  const resultNextStep = document.getElementById('checker-result-action');

  if (!birthYearSelect || !resultCard) return;

  function evaluateEligibility() {
    const year = parseInt(birthYearSelect.value, 10);
    const month = parseInt(birthMonthSelect.value, 10);

    if (!year || !month) return;

    resultCard.style.display = 'block';

    // Age turning in 2026:
    const ageIn2026 = 2026 - year;
    const ageIn2027 = 2027 - year;

    if (year === 2021) {
      // Turns 5 in 2026 -> Eligible for Grade R in 2027 (or early intake if turning 6 before 30 June 2027)
      resultBadge.textContent = 'Eligible for Grade R 2027 Intake';
      resultBadge.className = 'status-badge status-success';
      resultTitle.textContent = 'Apply Now for Grade R 2027';
      resultExplanation.innerHTML = `Your child will turn <strong>6 in 2027</strong>, satisfying the SASA Grade R entry criteria. Applications are handled <strong>directly by Laerskool Kempton Park</strong> (closing 9 October 2026). Intake is capped at 50 learners across 2 classes.`;
      resultNextStep.innerHTML = `<a href="#checklist" class="btn btn-gold btn-sm">Download Grade R Document Pack &rarr;</a>`;
    } else if (year === 2020) {
      // Turns 6 in 2026 -> Eligible for Grade R 2026 or Grade 1 in 2027
      resultBadge.textContent = 'Grade R (Current) or Grade 1 (2027)';
      resultBadge.className = 'status-badge status-primary';
      resultTitle.textContent = 'Eligible for Grade 1 (2027) or In-Year Grade R';
      resultExplanation.innerHTML = `Your child turns <strong>6 in 2026</strong> and will turn <strong>7 in 2027</strong>. For 2027 Grade 1 admission, applications must be submitted via the <strong>GDE Online Admissions Portal</strong> (gdeadmissions.gov.za) during the official window. For immediate 2026 Grade R transfer, please visit Ms. P. Moyaha at the front office.`;
      resultNextStep.innerHTML = `<a href="#gde-roadmap" class="btn btn-outline btn-sm">Review GDE Online Roadmap &rarr;</a>`;
    } else if (year <= 2019 && year >= 2013) {
      // Primary School Age (Grade 1 - 7)
      const estimatedGrade = Math.min(7, Math.max(1, 2026 - year - 6));
      resultBadge.textContent = `Grades 1–7 (Approx. Grade ${estimatedGrade})`;
      resultBadge.className = 'status-badge status-neutral';
      resultTitle.textContent = `Grade ${estimatedGrade} Enrolment Pathway`;
      resultExplanation.innerHTML = `Your child is of primary school age. New enrolments for Grades 1 to 7 are governed by the <strong>Gauteng Department of Education (GDE) Feeder Zone regulations</strong>. Feeder zones prioritize Kittyhawk / Rhodesfield residents and siblings of currently enrolled Kempies.`;
      resultNextStep.innerHTML = `<a href="#gde-roadmap" class="btn btn-outline btn-sm">View Feeder Zone Criteria &rarr;</a>`;
    } else if (year >= 2022) {
      // Future Learner
      resultBadge.textContent = 'Future Kempie (Under-Age for 2026/2027)';
      resultBadge.className = 'status-badge status-warning';
      resultTitle.textContent = 'Pre-Registration Interest';
      resultExplanation.innerHTML = `Your child is currently under the statutory Grade R entry age. You are welcome to subscribe to our open day notifications or join our Grade R waiting list for <strong>${year + 5}</strong>.`;
      resultNextStep.innerHTML = `<a href="contact.html" class="btn btn-outline-gold btn-sm">Contact Admissions Office &rarr;</a>`;
    }
  }

  birthYearSelect.addEventListener('change', evaluateEligibility);
  birthMonthSelect.addEventListener('change', evaluateEligibility);

  // Default evaluation
  evaluateEligibility();
}
