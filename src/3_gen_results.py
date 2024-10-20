from Functions import *

df = pd.read_csv('result.csv')

df['para'] = df['Param'].apply(lambda x: [eval(x)[2], eval(x)[0]])
df[['x', 'y']] = df['para'].apply(lambda x: pd.Series([x[0], x[1]]) if len(x) == 2 else pd.Series([x[0], x[0]])) 
print(df)

# draw heatmap
draw_thermodynamic_diagram(df, title="Sharpe under Different Parameters", z='Sharpe')  
