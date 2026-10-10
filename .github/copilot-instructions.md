# Copilot Instructions

## Objetivo do Projeto

Este projeto extrai lê as informações de um base fornecida em formato excel. 
De esta base extrae as linhas que deben ser aprobadas dentro de um portal
---

## Intruções de Implementação

Ao modificar arquivos:
 
- Nunca remover comentários existentes.
- Nunca remover docstrings.
- Preservar comentários de negócio e explicações técnicas.
- Ao adicionar código novo, adicionar comentários quando necessário.
- Priorizar manutenção da documentação existente.
- Alterar apenas o trecho solicitado e dar sugestões de outras melhorias.
- Quando não for possível implementar a funcionalidade solicitada, sugerir alternativas e explicar o motivo.

## Regras de formatação

- Limitar cada linha de código a no máximo 200 caracteres.
- Manter chamadas e definições de funções, métodos e construtores em uma única linha quando o comprimento total for menor ou igual a 200 caracteres.
- Não quebrar parâmetros em múltiplas linhas se a chamada inteira couber em até 200 caracteres.
- Não quebrar parâmetros em múltiplas linhas desnecessariamente.
- Só quebrar parâmetros em múltiplas linhas quando a chamada exceder 200 caracteres.
- Aplicar a mesma regra para:
  - funções
  - métodos
  - classes (construtores)
  - dicionários
  - listas
- Quando chamar o definir uma função o método deixar um espaçõ entre o nome da função e os parênteses.
- Quando definir variaveis ou parametros ou assignar valores, deixa espaços entre o nome da variável, o sinal de igual e o valor.
- Quando definir ou assignar o valor de um termo de uma variavei númeravel, deixar um espaçõ entre o nóme da variavel e os colchetes.

---

### Class CleanCases

Classe responsável por limpar a base de entrada "Cases", que será guardada dentro de uma variavel type dict da forma "self.data_dict ["Cases"]":

- A base "Cases" é uma tabela con as seguentes colunas:
    - report_id: Type str;
    - report_reference: Type str;
    - transaction_date: Type datetime;
    - month_year: Type str       
    - daycare_reference_month
    - gross_amount_cc
    - net_amount: Type float
    - max_daycare_amount: Type float
    - customer_category: Type str
    - employee_id: Type str
    - policy: Type str
    - has_daycare: Type bool
    - has_housing: Type bool
    - aprove_housing: Type bool
    - aprove_edv_housing: Type bool
    - aprove_guarderia: Type bool
    - aprove_km: Type bool
    - rules_approval: Type bool
    - can_be_approved: : Type str (variavel categorica)
    - __insert_utc_ts: Type datetime;
    - tope_actual: Type float
- Inicialmente temos a base sem limpar no arquivo Cases_sem_limpar.parquet dentro da pasta "bases". e será asignado o "self.data_dict ['Cases sem limpar']" igual ao DataFrame destes dados
- Apos a limpeza sera guardada a base cases no arquivo case_cleaned dentro do arquivo Cases_limpos.parquet dentro da pasta "bases" e será asignado o "self.data_dict ['Cases limpos']" igual ao DataFrame destes dados

---

#### Limpeza dos dados
    - Carregamos os dados da base "self.data_dict ['Cases sem limpar']"
    - Formatamos os tipos de dados de cada coluna
    - Tomamos os dados de "self.data_dict ['Cases sem limpar']"
    - Hacemos um agrupamento dos valores das columnas report_reference e __insert_utc_ts, agrupando por report_ference e com aggr function "max"; não indexar o agrupamento; salvamos na variavel group_cases o agrupamento.
    - Redefinimo a base "Cases limpos" filtrando só as linhas de "Cases sem limpar" que estão contidas dentro da tabela group_cases
    - Cria uma columna "Item" que númera linha por valor na columna "report_reference". Exemplo para report_reference = 1261-171921 os valores de Item são 1, 2, 3,...
    - Agrupamos usando multiindes, usando as columnas "report_frerence" e 'Item'.
    - Guardamos a base 'Cases limpos' com formato parquet dentro do arquivo 'Cases_limpos.parquet' dentro da pasta 'bases'

---

### Interface Web Streamlit

O projeto deve possuir uma interface web desenvolvida com Streamlit.
 
Arquivo principal:
 
    streamlit_app.py

Objetivo:

- Upload a base "Cases sem limpar" e guardar em 'Cases_sem_limpar.parquet' dentro da pasta 'bases'
- Executar a limpeza dos dados de 'Cases sem limpar' para obter a base 'Cases limpos'. Mara isto ussa uma estancia da classe Analisis en analisis.py
- Mostrar as bases
- As bases estarão guardadas dentro de uma variavel dict 'data_dict', exemplo 'data_dict [Cases sem limpar]' de forma similar a Class CleanCases

Fluxo:
1. O usuário acessa a interface web.
2. O usuário tem a possibilidade de upload a base 'Cases sem limpar'.
3. Apos de apertar um botão, a base 'Cases limpos' sera criada apartir da limpeza dos dados de 'Cases sem limpar'
4. As bases são exibidas separando estas em taps. Cada tap coresponde a base contida no data_dict e o nome corresponde a seu debido key em data_dict
5. Sempre mostra as bases existentes na pasta 'bases'. Assim podemos visualisar o que já foi procesado previamente, ignorando "Cases sem limpar"
6. O usuário tem a possibilidade de baixar os resultados em formato excel, en donde cada aba conten uma dada tabela da base, ignorando a base 'Cases sem limpar'.
7. O usuário terá a posibilidade de filtrar os dados por 'report_reference' e 'can_be_approved'
---

### Arquivo Mobile_Aprovation.bat

Cria um arquivo de lotes 'Mobile_Aprovation.bat".

Objetivo:
    - Ao clicar sobre este no windows, roda o streamlit_app.py, usando uv e streamlit.