import pandas as pd


def mock_rendimento(tipo, id_receita):
    if str(tipo).strip().lower() == 'produto final':
        return 1

    # Mock com rendimento menor para preparos/base de producao.
    # Faixa: 4 a 12 unidades.
    return 4 + ((int(id_receita) * 5) % 9)


def mock_preco_total(preco_atual, custo_receita, tipo):
    if pd.notna(preco_atual):
        return preco_atual

    if str(tipo).strip().lower() == 'produto final':
        return max(custo_receita * 2.8, 8.0)

    return max(custo_receita * 1.6, 10.0)

def main():
    input_file = 'fichas_tecnicas_estruturadas.xlsx'
    output_main = 'fichas_tecnicas_ids.xlsx'
    output_receitas = 'lista_receitas.xlsx'
    output_ingredientes = 'lista_ingredientes.xlsx'
    output_base_preenchida = 'fichas_tecnicas_estruturadas_preenchida.xlsx'
    
    try:
        print(f"Lendo o arquivo {input_file}...")
        df = pd.read_excel(input_file)
        
        # Verifica se as colunas necessárias existem
        if 'Receita' not in df.columns or 'Ingrediente' not in df.columns:
            print("Erro: As colunas 'Receita' e/ou 'Ingrediente' não foram encontradas no arquivo.")
            print(f"Colunas disponíveis: {df.columns.tolist()}")
            return

        if 'Custo_Receita' not in df.columns:
            print("Erro: A coluna 'Custo_Receita' não foi encontrada no arquivo.")
            print(f"Colunas disponíveis: {df.columns.tolist()}")
            return

        # Preenche Custo_Receita vazio com base no padrão observado nas linhas preenchidas:
        # custo da receita = soma do Custo_Ingrediente por (Tipo, Receita).
        soma_custo_por_receita = df.groupby(['Tipo', 'Receita'], dropna=False)['Custo_Ingrediente'].sum(min_count=1)
        custo_estimado = df.set_index(['Tipo', 'Receita']).index.map(soma_custo_por_receita)
        faltantes_antes = int(df['Custo_Receita'].isna().sum())
        df['Custo_Receita'] = df['Custo_Receita'].fillna(pd.Series(custo_estimado, index=df.index))
        faltantes_depois = int(df['Custo_Receita'].isna().sum())
        print(f"Custo_Receita preenchido: {faltantes_antes - faltantes_depois} linha(s)")

        # Cria IDs para valores únicos.
        df['ID_Receita'] = pd.factorize(df['Receita'])[0] + 1
        df['ID_Ingrediente'] = pd.factorize(df['Ingrediente'])[0] + 1

        # Tabela de receitas: Tipo fica aqui (nao na tabela de IDs) e inclui rendimento.
        receitas_df = (
            df[['ID_Receita', 'Receita', 'Tipo', 'Custo_Receita', 'Preco_Venda_Produto']]
            .drop_duplicates(subset=['ID_Receita'])
            .sort_values('ID_Receita')
            .reset_index(drop=True)
        )

        receitas_df['rendimento'] = receitas_df.apply(
            lambda row: mock_rendimento(row['Tipo'], row['ID_Receita']), axis=1
        )

        # Preco de venda e unitario: considera o valor atual como total da receita
        # e divide pelo rendimento para obter preco por unidade.
        preco_total = receitas_df.apply(
            lambda row: mock_preco_total(row['Preco_Venda_Produto'], row['Custo_Receita'], row['Tipo']),
            axis=1,
        )
        receitas_df['Preco_Venda_Produto'] = (preco_total / receitas_df['rendimento']).clip(lower=1.0)

        # Tabela de ingredientes: mantém características do ingrediente.
        ingredientes_df = (
            df[['ID_Ingrediente', 'Ingrediente', 'Un_Ingrediente', 'Preco_Un_Ingrediente']]
            .drop_duplicates(subset=['ID_Ingrediente'])
            .sort_values('ID_Ingrediente')
            .reset_index(drop=True)
        )

        # Tabela principal: apenas relação receita x ingrediente e seus números da relação.
        main_df = df.drop(
            columns=[
                'Receita',
                'Ingrediente',
                'Tipo',
                'Custo_Receita',
                'Preco_Venda_Produto',
                'Un_Ingrediente',
                'Preco_Un_Ingrediente',
            ]
        )

        # Reordena para deixar IDs no início.
        main_cols = ['ID_Receita', 'ID_Ingrediente'] + [
            c for c in main_df.columns if c not in ['ID_Receita', 'ID_Ingrediente']
        ]
        main_df = main_df[main_cols]

        # Arredonda todas as colunas numéricas (exceto IDs) para 2 casas.
        def arredondar_numericas(df_interno, excluir_colunas=None):
            excluir_colunas = excluir_colunas or []
            for col in df_interno.select_dtypes(include='number').columns:
                if col not in excluir_colunas:
                    df_interno[col] = df_interno[col].round(2)
            return df_interno

        main_df = arredondar_numericas(main_df, excluir_colunas=['ID_Receita', 'ID_Ingrediente'])
        receitas_df = arredondar_numericas(receitas_df, excluir_colunas=['ID_Receita'])
        ingredientes_df = arredondar_numericas(ingredientes_df, excluir_colunas=['ID_Ingrediente'])

        # Garante IDs inteiros.
        main_df['ID_Receita'] = main_df['ID_Receita'].astype(int)
        main_df['ID_Ingrediente'] = main_df['ID_Ingrediente'].astype(int)
        receitas_df['ID_Receita'] = receitas_df['ID_Receita'].astype(int)
        receitas_df['rendimento'] = receitas_df['rendimento'].astype(int)
        ingredientes_df['ID_Ingrediente'] = ingredientes_df['ID_Ingrediente'].astype(int)

        print("Arquivos sendo salvos...")
        df.to_excel(output_base_preenchida, index=False)
        main_df.to_excel(output_main, index=False)
        receitas_df.to_excel(output_receitas, index=False)
        ingredientes_df.to_excel(output_ingredientes, index=False)

        print(f"Base preenchida salva: {output_base_preenchida}")
        print(f"Arquivo principal salvo: {output_main}")
        print(f"Arquivo de receitas salvo: {output_receitas}")
        print(f"Arquivo de ingredientes salvo: {output_ingredientes}")
        
    except FileNotFoundError:
        print(f"Erro: O arquivo '{input_file}' não foi encontrado na pasta atual.")
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")

if __name__ == "__main__":
    main()
