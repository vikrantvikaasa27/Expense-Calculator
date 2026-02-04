"""Chart generation service for expense visualization."""

import io
from datetime import datetime
from decimal import Decimal

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict


class ChartService:
    """Service for generating expense charts and graphs."""
    
    def __init__(self):
        """Initialize chart styling."""
        plt.style.use('seaborn-v0_8-darkgrid')
        self.colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
        ]
    
    def generate_pie_chart(
        self, 
        category_data: dict[str, Decimal],
        title: str = "Expenses by Category"
    ) -> bytes:
        """
        Generate a pie chart for category-wise expenses.
        
        Args:
            category_data: Dict of category_name -> total_amount
            title: Chart title
            
        Returns:
            PNG image as bytes
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        labels = list(category_data.keys())
        sizes = [float(v) for v in category_data.values()]
        
        # Filter out zero values
        non_zero = [(l, s) for l, s in zip(labels, sizes) if s > 0]
        if not non_zero:
            return self._generate_empty_chart("No expenses to display")
        
        labels, sizes = zip(*non_zero)
        
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct=lambda pct: f'{pct:.1f}%\n(₹{pct/100*sum(sizes):.0f})',
            colors=self.colors[:len(labels)],
            explode=[0.02] * len(labels),
            shadow=True,
            startangle=90,
        )
        
        # Style the text
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # Add total in center
        total = sum(sizes)
        ax.text(0, 0, f'Total\n₹{total:,.0f}', ha='center', va='center', 
                fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        return self._fig_to_bytes(fig)
    
    def generate_bar_chart(
        self,
        daily_data: dict[str, Decimal],
        title: str = "Daily Expenses"
    ) -> bytes:
        """
        Generate a bar chart for daily expenses.
        
        Args:
            daily_data: Dict of date_string -> amount
            title: Chart title
            
        Returns:
            PNG image as bytes
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        dates = list(daily_data.keys())
        amounts = [float(v) for v in daily_data.values()]
        
        if not dates:
            return self._generate_empty_chart("No data available")
        
        bars = ax.bar(dates, amounts, color=self.colors[0], edgecolor='white', linewidth=0.7)
        
        # Add value labels on bars
        for bar, amount in zip(bars, amounts):
            if amount > 0:
                ax.text(
                    bar.get_x() + bar.get_width()/2,
                    bar.get_height() + max(amounts)*0.02,
                    f'₹{amount:.0f}',
                    ha='center',
                    va='bottom',
                    fontsize=8,
                    rotation=45
                )
        
        ax.set_xlabel('Date', fontsize=11)
        ax.set_ylabel('Amount (₹)', fontsize=11)
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # Rotate x labels
        plt.xticks(rotation=45, ha='right')
        
        # Add average line
        if amounts:
            avg = sum(amounts) / len(amounts)
            ax.axhline(y=avg, color='red', linestyle='--', linewidth=1.5, 
                      label=f'Average: ₹{avg:.0f}')
            ax.legend()
        
        plt.tight_layout()
        
        return self._fig_to_bytes(fig)
    
    def generate_trend_chart(
        self,
        monthly_data: dict[str, Decimal],
        title: str = "Monthly Expense Trend"
    ) -> bytes:
        """
        Generate a line chart for monthly expense trends.
        
        Args:
            monthly_data: Dict of month_string -> amount
            title: Chart title
            
        Returns:
            PNG image as bytes
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        months = list(monthly_data.keys())
        amounts = [float(v) for v in monthly_data.values()]
        
        if len(months) < 2:
            return self._generate_empty_chart("Need at least 2 months of data")
        
        ax.plot(months, amounts, marker='o', linewidth=2, markersize=8, 
                color=self.colors[1], markerfacecolor=self.colors[0])
        
        # Fill area under the line
        ax.fill_between(months, amounts, alpha=0.3, color=self.colors[1])
        
        # Add value labels
        for i, (month, amount) in enumerate(zip(months, amounts)):
            ax.annotate(
                f'₹{amount:,.0f}',
                (i, amount),
                textcoords="offset points",
                xytext=(0, 10),
                ha='center',
                fontsize=9
            )
        
        ax.set_xlabel('Month', fontsize=11)
        ax.set_ylabel('Amount (₹)', fontsize=11)
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        return self._fig_to_bytes(fig)
    
    def _generate_empty_chart(self, message: str) -> bytes:
        """Generate an empty chart with a message."""
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, message, ha='center', va='center', 
                fontsize=14, transform=ax.transAxes)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return self._fig_to_bytes(fig)
    
    def _fig_to_bytes(self, fig) -> bytes:
        """Convert matplotlib figure to PNG bytes."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return buf.read()


# Singleton instance
chart_service = ChartService()
