# Caso de uso real: Rio → Budapeste, volta de Berlim

Este documento mostra o verificador aplicado a uma viagem de verdade (preços lidos em 23/11/2026). É só um exemplo: a sua viagem é configurada por você (`python -m verificador.setup`).

**A viagem:** ida GIG → Budapeste (sáb 10/07/2027), volta Berlim → GIG (qui 22/07/2027), 2 adultos, econômica. A volta **não** sai de Budapeste ("open-jaw").

**As escolhas feitas na configuração:**
- Escala mínima de **4 horas** em toda conexão (tempo de imigração).
- Bagagem: **2 de mão + 1 despachada** por trecho (preço estimado de uma mala: R$ 600).
- Uma parada longa (~24h) numa cidade só valia se custasse **menos de R$ 1 mil** a mais.
- Aviso se o preço caísse 5% ou ficasse abaixo de R$ 18.000.

## Fotografia de 23/11/2026

| Fonte | Total para os 2 | Observação |
|---|---|---|
| **KLM Light** (Kayak e site da KLM) | **R$ 19.152** | Ida 21:55 (7h em Amsterdã), volta 06:00 (5h25 em Amsterdã). Sem mala despachada |
| KLM Light + 1 mala por trecho | ~R$ 20.350 | **Estimativa**: mala ~US$ 100–120 por trecho; o preço exato só aparece no fim da reserva |
| Lufthansa Economy Light | R$ 20.005 | Volta com 13h30–14h30 em Frankfurt, sem mala despachada |
| Google Voos (série automática) | R$ 21.440 | Lista menos opções que o Kayak; compare-o só com o dia anterior dele mesmo |
| CVC (Turkish, mala incluída) | R$ 20.035 | **Reprovada**: escala de 3h15 em Istambul na volta |
| Paradas de ~24h (Londres, Lisboa, Madri) | R$ 22.189 a 24.826 | ≥ R$ 3 mil acima: fora pela regra do R$ 1 mil |
| Flying Blue (milhas) | 502.000 milhas + taxas | Equilíbrio ≈ R$ 32 por milheiro |
| Smiles (milhas) | mais de 3× o Flying Blue | 330.500 a 360.700 milhas por pessoa, só na ida |

Conclusão daquele dia: **pagar em dinheiro a KLM Light** era o melhor caminho; milhas só ganham com milheiro abaixo de ~R$ 30.

Os documentos de desenho e plano (`2026-11-23-verificador-passagens-design.md` e `superpowers/plans/`) foram escritos para este caso.
