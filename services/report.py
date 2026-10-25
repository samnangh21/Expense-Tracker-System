"""Reports built with Pandas. Both functions take a list of Transaction objects."""

import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
import calendar

def to_dataframe(transactions):
    """Turn a list of Transaction objects into a table (DataFrame)."""
    return pd.DataFrame([t.to_dict() for t in transactions])


def category_report(transactions):
    """Total and count for each category, split into income and expense."""
    df = to_dataframe(transactions)
    result = (
        df.groupby(["type", "category"])["amount"]
        .agg(total="sum", count="count")
        .reset_index()
    )
    result = result.sort_values(["type", "total"], ascending=[True, False])
    result["total"] = result["total"].round(2)
    return result


def monthly_report(transactions):
    """Income, expense and balance for each month (MM-YYYY)."""
    df = to_dataframe(transactions)
    df["month"] = pd.to_datetime(df["date"], format="%d-%m-%Y").dt.strftime("%m-%Y")
    table = df.pivot_table(
        index="month", columns="type", values="amount", aggfunc="sum", fill_value=0
    )
    table = table.reindex(columns=["income", "expense"], fill_value=0)
    table["balance"] = table["income"] - table["expense"]
    table.columns.name = None
    return table.round(2)



def income_expense_line_chart(transactions, username):
    """Line graph comparing income (positive) and expenses (negative) over time, for one month."""
    df = to_dataframe(transactions)
    if df.empty:
        print("No transactions to chart.")
        return
    df["date_parsed"] = pd.to_datetime(df["date"], format="%d-%m-%Y")

    income_daily = (df[df["type"] == "income"]
                    .groupby("date_parsed")["amount"].sum().sort_index())
    expense_daily = (df[df["type"] == "expense"]
                     .groupby("date_parsed")["amount"].sum().sort_index())
    expense_daily = -expense_daily  # show expenses below the zero line

    fig, ax = plt.subplots(figsize=(14, 5))
    if not income_daily.empty:
        ax.plot(income_daily.index, income_daily.values, marker="o",
                color="green", label="Income")
    if not expense_daily.empty:
        ax.plot(expense_daily.index, expense_daily.values, marker="o",
                color="red", label="Expense")

    ax.axhline(0, color="grey", linewidth=1)  # zero line for reference

    ax.set_title(f"Income vs Expenses - {username}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Amount")
    ax.legend()

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))

    year, month = df["date_parsed"].iloc[0].year, df["date_parsed"].iloc[0].month
    last_day = calendar.monthrange(year, month)[1]
    ax.set_xlim(pd.Timestamp(year=year, month=month, day=1),
                pd.Timestamp(year=year, month=month, day=last_day))

    fig.autofmt_xdate(rotation=45)
    plt.tight_layout()
    plt.show()


def expense_pie_chart(transactions, username):
    """Pie Chart of Expense Totals By Category."""
    df = to_dataframe(transactions)
    expenses = df[df["type"] == "expense"]
    if expenses.empty:
        print("No Expenses To Chart.")
        return
    by_category = expenses.groupby("category")["amount"].sum()

    plt.figure(figsize=(6, 6))
    plt.pie(by_category.values, labels=by_category.index, autopct="%1.1f%%")
    plt.title(f"Expenses By Category - {username}")
    plt.tight_layout()
    plt.show()