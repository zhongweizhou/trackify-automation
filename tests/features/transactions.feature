Feature: Transactions List

  Background:
    Given app is launched with a clean database
    And user enters the configured environment name and continues
    And user selects the configured environment currency and sets monthly budget "30000"
    And user applies the configured Bank SMS Reader setting and gets started
    And user is on the Home page

# scenario_id: TC_TXN_001
# introduced_in: 1.0.0
# platforms: android, ios
  @p1 @filter
  Scenario: Filter transactions by type shows only matching type
    When user taps "Add Expense"
    And user enters amount "100"
    And user selects category "Food"
    And user enters tags "filter,expense"
    And user taps Save
    And user taps "Add Income"
    And user enters amount "5000"
    And user selects category "Salary"
    And user enters tags "filter,income"
    And user taps Save
    And user navigates to the Transactions page
    And user filters transactions by type "expense"
    Then only transactions of type "expense" are shown

# scenario_id: TC_TXN_002
# introduced_in: 1.0.0
# platforms: android, ios
  @p1 @grouping
  Scenario: Transactions grouped by date with section headers
    When user taps "Add Expense"
    And user enters amount "100"
    And user selects category "Food"
    And user enters tags "history,expense"
    And user selects transaction date and time "20250506 9:00 AM"
    And user taps Save
    And user navigates to the Transactions page
    Then transactions are grouped by date with section headers
