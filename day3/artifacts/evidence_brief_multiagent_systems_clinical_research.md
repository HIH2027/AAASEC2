# Evidence Brief: Safe Use of Multi-Agent Systems in Clinical Research

## Question
What are the key considerations, benefits, and risks for ensuring the safe use of multi-agent systems (MAS) in clinical research settings?

## Executive summary
Multi-agent systems offer potential benefits for clinical research, including improved data integration, automation of complex workflows, and enhanced decision support through distributed intelligence. However, their use introduces safety concerns related to accountability, bias, data privacy, and unpredictable interactions between agents. Current evidence on MAS in clinical research is limited, with most insights derived from theoretical frameworks, early pilots, and adjacent fields such as AI safety and distributed systems. Key recommendations include establishing robust governance frameworks, implementing rigorous validation and monitoring protocols, ensuring human oversight, and conducting further empirical studies to evaluate safety and efficacy in real-world research contexts.

## Evidence supplied
1. Goh, A. et al. **AI Agents in Clinical Medicine: A Systematic Review.** Peer-reviewed systematic review of 20 clinical-agent studies, including multi-agent collaboration and tool use. https://pmc.ncbi.nlm.nih.gov/articles/PMC12407621/
2. **Multi-agent systems for clinical decision support: A systematic review.** *Applied Soft Computing* (2025). Reviews 42 studies and identifies explainability, hierarchy, adaptability, and semantic-integration gaps. https://doi.org/10.1016/j.asoc.2025.114447
3. **Artificial intelligence agents in healthcare research: A scoping review.** Maps agent architectures and identifies gaps in long-term safety, efficacy, and real-world integration. https://pmc.ncbi.nlm.nih.gov/articles/PMC12890167/
4. International Council for Harmonisation / U.S. FDA. **E6(R3) Good Clinical Practice.** Final FDA guidance, September 2025. https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e6r3-good-clinical-practice-gcp
5. European Medicines Agency. **Reflection paper on the use of Artificial Intelligence in the medicinal product lifecycle.** EMA/CHMP/CVMP/83833/2023, adopted September 2024. https://www.ema.europa.eu/en/use-artificial-intelligence-ai-medicinal-product-lifecycle-scientific-guideline
6. U.S. FDA. **Using Artificial Intelligence & Machine Learning in the Development of Drug and Biological Products.** Discussion paper, May 2023. https://www.fda.gov/media/167973/download
7. World Health Organization. **Ethics and governance of artificial intelligence for health.** WHO guidance, 2021. https://www.who.int/publications/i/item/9789240029200
8. National Institute of Standards and Technology. **Artificial Intelligence Risk Management Framework (AI RMF 1.0).** NIST AI 100-1, 2023. https://doi.org/10.6028/NIST.AI.100-1
9. U.S. FDA. **Electronic Systems, Electronic Records, and Electronic Signatures in Clinical Investigations: Questions and Answers.** Final guidance, October 2024. https://www.fda.gov/regulatory-information/search-fda-guidance-documents/electronic-systems-electronic-records-and-electronic-signatures-clinical-investigations-questions
10. U.S. FDA. **Guidance for Industry: Computerized Systems Used in Clinical Trials.** Audit-trail and record-reliability principles relevant to 21 CFR Part 11. https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/fda-bioresearch-monitoring-information/guidance-industry-computerized-systems-used-clinical-trials
11. U.S. Department of Health and Human Services. **The HIPAA Security Rule.** Current overview of safeguards for electronic protected health information. https://www.hhs.gov/hipaa/for-professionals/security/index.html This revised brief uses a targeted evidence base consisting of peer-reviewed reviews of healthcare AI agents and multi-agent clinical decision support, plus primary guidance from ICH/FDA, EMA, WHO, NIST, and HHS. The regulatory and governance documents address AI or computerized systems broadly rather than MAS specifically; applying them to MAS is therefore an evidence-informed extrapolation.

## Key findings
- **Potential benefits (interpretation):** MAS can distribute complex tasks across specialized agents (e.g., data collection, analysis, protocol monitoring), potentially increasing efficiency and enabling adaptive trial designs.
- **Safety risks (interpretation):** Risks include unclear liability for agent actions, propagation of biases from training data, emergent behaviors from agent interactions, and challenges in ensuring data privacy and security.
- **Governance and oversight (proposal):** Safe use likely requires clear accountability structures, predefined operational limits for agents, real-time monitoring, and mandatory human-in-the-loop oversight for critical decisions.
- **Validation needs (proposal):** Agents should undergo rigorous verification and validation, including testing for robustness, fairness, and compliance with regulatory standards (e.g., GDPR, HIPAA, 21 CFR Part 11) before deployment in research.
- **Evidence gap (interpretation):** Empirical evidence on the safety and effectiveness of MAS in actual clinical research trials is scarce; most available literature consists of conceptual papers, simulations, or applications in non-clinical domains.

## Uncertainty and limitations
- The brief lacks sourced facts because no user-provided evidence was supplied; all claims are interpretive or proposal-based.
- Rapid technological advances mean that specific risks and mitigation strategies may evolve quickly.
- Regulatory frameworks for AI-based systems in clinical research are still developing, creating uncertainty about compliance requirements.
- The generalizability of findings from MAS in other domains (e.g., manufacturing, finance) to clinical research is uncertain due to the high-stakes, regulated nature of human subjects research.

## Recommended next steps
1. **For researchers and institutions:** Conduct a systematic review of existing literature on MAS and AI safety in healthcare to identify empirical studies and case reports.
2. **For developers:** Implement transparency and traceability mechanisms in MAS designs to facilitate auditing and accountability.
3. **For ethics boards and regulators:** Develop specific guidance documents addressing the use of autonomous and semi-autonomous agents in clinical trials, focusing on risk assessment, informed consent, and ongoing monitoring.
4. **For pilot projects:** Initiate small-scale, closely monitored studies that use MAS for non-critical tasks (e.g., administrative workflow automation) to gather real-world safety and performance data before scaling to patient-intervention functions.
5. **For ongoing evaluation:** Establish multidisciplinary oversight committees that include clinicians, data scientists, ethicists, and patient representatives to review MAS deployments regularly.

## Sources
1. Goh, A. et al. **AI Agents in Clinical Medicine: A Systematic Review.** Peer-reviewed systematic review of 20 clinical-agent studies, including multi-agent collaboration and tool use. https://pmc.ncbi.nlm.nih.gov/articles/PMC12407621/
2. **Multi-agent systems for clinical decision support: A systematic review.** *Applied Soft Computing* (2025). Reviews 42 studies and identifies explainability, hierarchy, adaptability, and semantic-integration gaps. https://doi.org/10.1016/j.asoc.2025.114447
3. **Artificial intelligence agents in healthcare research: A scoping review.** Maps agent architectures and identifies gaps in long-term safety, efficacy, and real-world integration. https://pmc.ncbi.nlm.nih.gov/articles/PMC12890167/
4. International Council for Harmonisation / U.S. FDA. **E6(R3) Good Clinical Practice.** Final FDA guidance, September 2025. https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e6r3-good-clinical-practice-gcp
5. European Medicines Agency. **Reflection paper on the use of Artificial Intelligence in the medicinal product lifecycle.** EMA/CHMP/CVMP/83833/2023, adopted September 2024. https://www.ema.europa.eu/en/use-artificial-intelligence-ai-medicinal-product-lifecycle-scientific-guideline
6. U.S. FDA. **Using Artificial Intelligence & Machine Learning in the Development of Drug and Biological Products.** Discussion paper, May 2023. https://www.fda.gov/media/167973/download
7. World Health Organization. **Ethics and governance of artificial intelligence for health.** WHO guidance, 2021. https://www.who.int/publications/i/item/9789240029200
8. National Institute of Standards and Technology. **Artificial Intelligence Risk Management Framework (AI RMF 1.0).** NIST AI 100-1, 2023. https://doi.org/10.6028/NIST.AI.100-1
9. U.S. FDA. **Electronic Systems, Electronic Records, and Electronic Signatures in Clinical Investigations: Questions and Answers.** Final guidance, October 2024. https://www.fda.gov/regulatory-information/search-fda-guidance-documents/electronic-systems-electronic-records-and-electronic-signatures-clinical-investigations-questions
10. U.S. FDA. **Guidance for Industry: Computerized Systems Used in Clinical Trials.** Audit-trail and record-reliability principles relevant to 21 CFR Part 11. https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/fda-bioresearch-monitoring-information/guidance-industry-computerized-systems-used-clinical-trials
11. U.S. Department of Health and Human Services. **The HIPAA Security Rule.** Current overview of safeguards for electronic protected health information. https://www.hhs.gov/hipaa/for-professionals/security/index.html
