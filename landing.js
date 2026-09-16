(() => {
  'use strict';

  const details = {
    design: {
      kicker: 'RAC // STAGE 01',
      title: 'Design',
      summary: 'Candidate creation is intentionally upstream of evidence. A browser-generated or hand-authored pattern is a hypothesis, not a result.',
      input: 'Pattern parameters, references, style constraints, seeds, and declared generation configuration.',
      output: 'A candidate artifact with reproducible configuration and identity.',
      boundary: 'Exploration output cannot self-promote into measured evidence.',
      evidence: 'Normally RAC-D0 until a governed experiment produces admissible measurements.',
      why: 'Separating invention from evaluation prevents attractive outputs from inheriting credibility they have not earned.'
    },
    screen: {
      kicker: 'RAC // STAGE 02',
      title: 'Surrogate screening',
      summary: 'Low-cost surrogate evaluation decides whether a candidate earns more expensive research without consuming held-out evidence.',
      input: 'Declared candidate plus preregistered surrogate systems and screening rules.',
      output: 'Screening observations, closure state, and either survivor eligibility or a retained negative.',
      boundary: 'Held-out certification data stays unavailable during generation and screening unless a new governed experiment explicitly permits it.',
      evidence: 'Can support RAC-D1 when the declared surrogate evidence requirements are met.',
      why: 'Cheap early rejection preserves scientific independence and makes negative results useful instead of disposable.'
    },
    simulate: {
      kicker: 'RAC // STAGE 03',
      title: 'Simulation / EOT',
      summary: 'RAC evaluates whether a candidate remains coherent under transformations that approximate deformation, viewpoint, pose, lighting, and print constraints.',
      input: 'Candidate artifact plus frozen transformation and simulation configuration.',
      output: 'Transformation-aware observations and reproducible simulation artifacts.',
      boundary: 'Simulation is still digital evidence. It cannot substitute for matched physical capture.',
      evidence: 'Research evidence that can inform candidate selection and digital evaluation.',
      why: 'Physical garments bend, wrinkle, rotate, scale, and move; a flat digital success is not enough.'
    },
    evaluate: {
      kicker: 'RAC // STAGE 04',
      title: 'Frozen digital evaluation',
      summary: 'Candidate measurements are performed under declared model identities, preprocessing, thresholds, fixtures, and validity rules.',
      input: 'Frozen candidate, evaluator/model set, preprocessing, thresholds, fixtures, and protocol.',
      output: 'Raw rows, aggregates, validity states, provenance, and numerical verification inputs.',
      boundary: 'Control-undetectable or otherwise invalid observations cannot count as adversarial success.',
      evidence: 'Eligible for RAC-D2 only when the held-out and issuance rules are actually satisfied.',
      why: 'A score without frozen context is difficult to reproduce and easy to overstate.'
    },
    gate: {
      kicker: 'RAC // STAGE 05',
      title: 'Evidence gate',
      summary: 'The certification layer decides whether the evidence supports promotion, must remain at its current state, or should be refused.',
      input: 'Preregistered protocol, artifact hashes, source commit, evidence records, model metadata, validity checks, and required physical/manufacturing inputs.',
      output: 'A bounded evidence state, sealed bundle, retained negative, or explicit refusal.',
      boundary: 'Missing hashes, illegal state transitions, missing physical evidence, and malformed inputs fail closed.',
      evidence: 'RAC-D0 → D1 → D2 → P1 → P2 → M1 → M2, with hard type boundaries.',
      why: 'The gate prevents software completion or digital performance from silently becoming a physical product claim.'
    },
    produce: {
      kicker: 'RAC // STAGE 06',
      title: 'Production release',
      summary: 'The production path binds the exact approved artwork and vendor/template identity before physical spend or fabrication.',
      input: 'Verified artwork source, vendor intake, placements, sizing, hashes, and operator review.',
      output: 'Deterministic production artifacts, archives, and readiness records.',
      boundary: 'The release wrapper validates readiness but does not authorize spend or invent manufacturing evidence.',
      evidence: 'Production provenance supporting later RAC-M states only when corresponding manufacturing measurements exist.',
      why: 'A printed garment must remain the same object the research protocol intended to test.'
    },
    physical: {
      kicker: 'RAC // STAGE 07',
      title: 'Matched physical trial',
      summary: 'Physical testing compares candidate and control under frozen, matched conditions and records the capture identities required for admissible evidence.',
      input: 'Candidate/control garments, calibration state, camera identity, distance, angle, pose, lighting, wash state, schedule, and pairing randomization.',
      output: 'Sealed physical captures, analysis outputs, statistics, and traceable trial-store entries.',
      boundary: 'RAC-P1 is unavailable until admissible matched physical evidence is actually collected and analyzed.',
      evidence: 'Controlled physical evidence for RAC-P1; durability/retest evidence is required for RAC-P2.',
      why: 'Physical efficacy is a measurement problem, not a software inference.'
    },
    exploration: {
      kicker: 'RAC // PLANE 01',
      title: 'Exploration plane',
      summary: 'The fast creative surface where patterns can be generated, varied, visualized, simulated, and exported without pretending those actions are certification.',
      input: 'Ideas, pattern parameters, references, palettes, seeds, and local browser controls.',
      output: 'Candidates, previews, heuristic analysis, and research questions.',
      boundary: 'Exploration metrics and local proxies cannot silently become measured detector or physical-efficacy claims.',
      evidence: 'Typically candidate-level context, not certification evidence.',
      why: 'Researchers need speed during ideation without weakening later scientific boundaries.'
    },
    research: {
      kicker: 'RAC // PLANE 02',
      title: 'Research plane',
      summary: 'The governed experimental layer for screening, optimization, transformation, evaluator adapters, and reproducible digital experiments.',
      input: 'Frozen experiment contracts, candidates, model sets, fixtures, and transformation policies.',
      output: 'Measured digital artifacts, closures, negative results, and experiment records.',
      boundary: 'Surrogate and held-out roles remain distinct; closed experiments are not retroactively rewritten.',
      evidence: 'Produces digital evidence that may qualify for RAC-D1 or RAC-D2 under the certification rules.',
      why: 'Repeatable experimentation requires stronger controls than a demo interface.'
    },
    certification: {
      kicker: 'RAC // PLANE 03',
      title: 'Certification & evidence plane',
      summary: 'The internal verification framework that binds evidence type, source, configuration, artifact identity, provenance, and state transitions.',
      input: 'Evidence records, hashes, protocols, model metadata, physical/manufacturing records, and source identity.',
      output: 'Sealed evidence bundles, state decisions, certificates when eligible, or explicit refusal.',
      boundary: 'It is an internal evidence framework—not independent accredited certification and not a universal surveillance guarantee.',
      evidence: 'Defines and enforces RAC-D0, D1, D2, P1, P2, M1, and M2.',
      why: 'The evidence object should say exactly what was measured, under which rules, and what the result does not prove.'
    },
    validation: {
      kicker: 'RAC // PLANE 04',
      title: 'Physical validation plane',
      summary: 'The production and capture layer that turns a hash-bound candidate into a matched physical experiment and, later, manufacturing evidence.',
      input: 'Verified production source, garments, vendor artifacts, calibration, capture schedule, and operator procedure.',
      output: 'Physical trial evidence, durability results, golden-sample records, and lot-conformity measurements.',
      boundary: 'Current physical P1 evidence remains open; product physical efficacy is not supported until the frozen trial path is executed.',
      evidence: 'RAC-P1/P2 and, with manufacturing evidence, RAC-M1/M2.',
      why: 'The garment in the real scene—not the digital preview—is the object that physical claims are about.'
    }
  };

  const dialog = document.getElementById('detailDialog');
  const close = document.getElementById('detailClose');
  const fields = {
    kicker: document.getElementById('detailKicker'),
    title: document.getElementById('detailTitle'),
    summary: document.getElementById('detailSummary'),
    input: document.getElementById('detailInput'),
    output: document.getElementById('detailOutput'),
    boundary: document.getElementById('detailBoundary'),
    evidence: document.getElementById('detailEvidence'),
    why: document.getElementById('detailWhy')
  };

  function openDetail(key) {
    const item = details[key];
    if (!item || !dialog) return;
    Object.keys(fields).forEach(name => {
      if (fields[name]) fields[name].textContent = item[name] || '';
    });
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
  }

  document.querySelectorAll('[data-detail]').forEach(button => {
    button.addEventListener('click', () => openDetail(button.dataset.detail));
  });

  if (close) {
    close.addEventListener('click', () => {
      if (typeof dialog.close === 'function') dialog.close();
      else dialog.removeAttribute('open');
    });
  }

  if (dialog) {
    dialog.addEventListener('click', event => {
      const rect = dialog.getBoundingClientRect();
      const outside =
        event.clientX < rect.left || event.clientX > rect.right ||
        event.clientY < rect.top || event.clientY > rect.bottom;
      if (outside && typeof dialog.close === 'function') dialog.close();
    });
  }

  const reveal = document.querySelectorAll('.reveal');
  const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!('IntersectionObserver' in window) || reduced) {
    reveal.forEach(node => node.classList.add('visible'));
  } else {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' });
    reveal.forEach(node => observer.observe(node));
  }
})();
