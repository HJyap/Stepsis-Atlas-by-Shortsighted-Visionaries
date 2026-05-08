export const testChatResponses = {
  lactate_mortality: {
    response:
      "I found evidence in the uploaded articles that higher initial lactate is associated with higher 28-day mortality.",
  },
  sofa_mortality: {
    response:
      "The uploaded articles show that higher SOFA scores are associated with higher ICU and 28-day mortality across the matched studies.",
  },
  antibiotic_timing: {
    response:
      "The matched studies suggest earlier antibiotic administration is associated with better survival outcomes in sepsis cohorts.",
  },
  septic_shock: {
    response:
      "I found multiple references focused on septic shock populations in the uploaded articles, including outcome and severity data.",
  },
  geographic_comparison: {
    response:
      "I found limited geographic comparison data in the uploaded articles, with study populations varying by ICU setting and sepsis cohort.",
  },
  not_found: {
    response: "I could not find evidence for that in the uploaded articles.",
  },
};

export const articleResults = {
  lactate_mortality: {
    status: "found",
    query: "What is the relationship between initial lactate and 28-day mortality?",
    answer: testChatResponses.lactate_mortality.response,
    references: [
      {
        study: "Smith et al.",
        year: 2021,
        population: "Septic shock",
        source: "Page 4, Table 2",
        excerpt:
          "Patients with higher admission lactate had increased 28-day mortality.",
        lactate: 4.2,
        mortality: 32,
        confidence: "91%",
      },
      {
        study: "Chen et al.",
        year: 2019,
        population: "ICU sepsis",
        source: "Page 5, Table 3",
        excerpt:
          "Initial lactate remained positively associated with mortality across ICU sepsis cases.",
        lactate: 5.1,
        mortality: 41,
        confidence: "93%",
      },
    ],
  },
  sofa_mortality: {
    status: "found",
    query: "How does SOFA score relate to mortality in the uploaded articles?",
    answer: testChatResponses.sofa_mortality.response,
    references: [
      {
        study: "Smith et al.",
        year: 2021,
        population: "Septic shock",
        source: "Page 4, Table 2",
        excerpt:
          "SOFA score tracked with mortality risk in the severe sepsis subgroup.",
        lactate: 4.2,
        mortality: 32,
        confidence: "91%",
      },
      {
        study: "Patel et al.",
        year: 2022,
        population: "Septic shock",
        source: "Page 7, Table 1",
        excerpt:
          "Higher baseline SOFA scores were associated with worse 28-day survival.",
        lactate: 4.7,
        mortality: 38,
        confidence: "89%",
      },
    ],
  },
  antibiotic_timing: {
    status: "found",
    query: "What do the uploaded articles say about antibiotic timing and survival?",
    answer: testChatResponses.antibiotic_timing.response,
    references: [
      {
        study: "Garcia et al.",
        year: 2020,
        population: "Severe sepsis",
        source: "Page 6, Results",
        excerpt:
          "Shorter time to antibiotics was associated with lower mortality in severe sepsis patients.",
        lactate: 3.6,
        mortality: 25,
        confidence: "86%",
      },
      {
        study: "Johnson et al.",
        year: 2018,
        population: "Severe sepsis",
        source: "Page 3, Results",
        excerpt:
          "Earlier antibiotic treatment aligned with improved short-term survival.",
        lactate: 3.3,
        mortality: 22,
        confidence: "84%",
      },
    ],
  },
  septic_shock: {
    status: "found",
    query: "What data do the uploaded articles have on septic shock patients?",
    answer: testChatResponses.septic_shock.response,
    references: [
      {
        study: "Smith et al.",
        year: 2021,
        population: "Septic shock",
        source: "Page 4, Table 2",
        excerpt:
          "The septic shock cohort had elevated lactate and a higher 28-day mortality profile.",
        lactate: 4.2,
        mortality: 32,
        confidence: "91%",
      },
      {
        study: "Patel et al.",
        year: 2022,
        population: "Septic shock",
        source: "Page 7, Table 1",
        excerpt:
          "Patients with septic shock demonstrated persistent organ dysfunction and higher mortality.",
        lactate: 4.7,
        mortality: 38,
        confidence: "89%",
      },
    ],
  },
  geographic_comparison: {
    status: "found",
    query: "Is there any geographic or regional comparison in the uploaded articles?",
    answer: testChatResponses.geographic_comparison.response,
    references: [
      {
        study: "Garcia et al.",
        year: 2020,
        population: "Severe sepsis",
        source: "Page 6, Results",
        excerpt:
          "The study described regional ICU enrollment differences without a strong pooled comparison outcome.",
        lactate: 3.6,
        mortality: 25,
        confidence: "86%",
      },
    ],
  },
  not_found: {
    status: "not_found",
    query: "Does vitamin D reduce sepsis mortality in the uploaded articles?",
    answer: testChatResponses.not_found.response,
    references: [],
  },
};

export function matchQueryKey(query) {
  const userQuery = query.toLowerCase();

  if (
    userQuery.includes("lactate") ||
    (userQuery.includes("mortality") && userQuery.includes("admission"))
  ) {
    return "lactate_mortality";
  }

  if (
    userQuery.includes("sofa") ||
    (userQuery.includes("organ failure") && userQuery.includes("mortality"))
  ) {
    return "sofa_mortality";
  }

  if (
    userQuery.includes("antibiotic timing") ||
    userQuery.includes("time to antibiotic") ||
    userQuery.includes("antibiotic") ||
    userQuery.includes("survival")
  ) {
    return "antibiotic_timing";
  }

  if (
    userQuery.includes("septic shock") ||
    userQuery.includes("shock cohort") ||
    userQuery.includes("shock patients")
  ) {
    return "septic_shock";
  }

  if (
    userQuery.includes("geographic") ||
    userQuery.includes("region") ||
    userQuery.includes("regional") ||
    userQuery.includes("country")
  ) {
    return "geographic_comparison";
  }

  return "not_found";
}

export function getArticleResultFromQuery(query) {
  const key = matchQueryKey(query);
  return articleResults[key];
}
