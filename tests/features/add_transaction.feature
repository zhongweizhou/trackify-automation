Feature: Add Transaction

  Background:
    Given app is launched with a clean database
    And user is on the Home page

  @smoke @p0
  Scenario: Add expense happy path
    When user taps "Add Expense"
    And user enters amount "100"
    And user selects category "Food"
    And user enters note "breakfast"
    And user taps Save
    Then transaction appears in Recent transactions with amount "100.0"

  @skip @smoke @p0
  Scenario: Add income happy path
    When user taps "Add Income"
    And user enters amount "5000"
    And user selects category "Salary"
    And user taps Save
    Then transaction appears in Recent transactions with amount "5000.0"

  @skip @smoke @p0
  Scenario: Add transfer happy path
    When user taps "Add Transfer"
    And user enters amount "200"
    And user selects category "Food"
    And user taps Save
    Then transaction appears in Recent transactions with amount "200.0"

  @skip @smoke @p0
  Scenario: Validation — empty amount shows error and does not save
    When user taps "Add Expense"
    And user leaves amount empty
    And user selects category "Food"
    And user taps Save
    Then error message "Amount is required" is shown for amount
    And no transaction appears in Recent transactions

  @skip @p1 @custom_category
  Scenario: Add expense with new custom category created in flow
    When user taps "Add Expense"
    And user enters amount "50"
    And user taps "Add new category"
    And user creates custom category "Coffee"
    And user taps Save
    Then transaction appears in Recent transactions with amount "50.0"
    And no transaction appears in Recent transactions with category "Coffee" missing
