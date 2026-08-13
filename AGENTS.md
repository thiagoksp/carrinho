# Instruções do projeto Carrinho

## Objetivo

Construir, passo a passo, um agente de mercado que recebe orçamento, dias, disposição para cozinhar e itens existentes; gera plano de refeições e lista de compras; e futuramente pesquisa preços e monta carrinhos.

## Forma de trabalhar

- Avance em etapas pequenas, explicadas em linguagem acessível.
- Reduza o número de decisões apresentadas ao usuário.
- Antes de cada nova etapa, confirme o resultado da etapa anterior.
- Não implemente funcionalidades além da etapa solicitada.
- Não adicione bibliotecas, serviços, plugins ou infraestrutura sem necessidade concreta.
- Preserve simplicidade e facilidade de aprendizado acima de arquitetura prematura.

## Escopo atual

A interface inicial é o terminal. O programa identifica, completa e confirma os dados. O planejamento por regras ajusta pessoas, dias, embalagens, itens existentes e orçamento em CAD, sem serviços externos. Quando necessário, tenta uma alternativa econômica e informa se ela ainda ultrapassar o orçamento. Somente ausência de restrições ou restrição à lactose são suportadas nesta etapa.

## Evolução prevista

1. Texto do usuário para plano de refeições e lista de compras.
2. Quantidades e respeito ao orçamento.
3. Pesquisa de produtos e preços reais.
4. Otimização por loja ou combinação de lojas.
5. Montagem do carrinho de compras.
