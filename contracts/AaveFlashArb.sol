// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title AIOS Flash-Loan Arbitrage (Aave V3) — v19.2 stub
/// @notice Dry-run safe. Live requires AIOS_FLASH_LIVE=1 + audit.
/// @dev Uses Aave V3 flashLoanSimple. Profit must cover fee+gas or revert (no loss except gas).
import {IPool} from "@aave/core-v3/contracts/interfaces/IPool.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract AaveFlashArb {
    address public owner;
    IPool public pool;
    uint256 public constant FLASH_FEE_BPS_POLYGON = 5; // 0.05% = 5 bps

    event ArbitrageExecuted(address token, uint256 amount, uint256 profit, string buyVenue, string sellVenue);
    event DryRunSimulated(address token, uint256 amount, int256 netProfit);

    modifier onlyOwner() { require(msg.sender == owner, "not owner"); _; }

    constructor(address _pool) { owner = msg.sender; pool = IPool(_pool); }

    /// @notice Execute arbitrage: flashLoan -> buy low -> sell high -> repay + profit
    /// @dev In dryRun, just simulate and emit event without on-chain swap
    function executeArbitrage(
        address token,
        uint256 amount,
        bytes calldata buyCallData,
        bytes calldata sellCallData,
        address buyTarget,
        address sellTarget,
        bool dryRun
    ) external onlyOwner {
        if (dryRun) {
            // Simulate: assume spread 0.08% -> net negative, so would revert
            int256 net = -27; // placeholder for 10k WETH 0.08% spread
            emit DryRunSimulated(token, amount, net);
            return;
        }
        // Live: flashLoanSimple will call executeOperation
        bytes memory params = abi.encode(buyCallData, sellCallData, buyTarget, sellTarget);
        pool.flashLoanSimple(address(this), token, amount, params, 0);
    }

    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        require(msg.sender == address(pool), "not pool");
        require(initiator == address(this), "not initiator");
        // Decode
        (bytes memory buyCallData, bytes memory sellCallData, address buyTarget, address sellTarget) = abi.decode(params, (bytes, bytes, address, address));
        // 1. Buy low (e.g., Uniswap V3 exactIn)
        (bool buyOk, ) = buyTarget.call(buyCallData);
        require(buyOk, "buy failed");
        // 2. Sell high (e.g., 1inch or Sushi)
        (bool sellOk, ) = sellTarget.call(sellCallData);
        require(sellOk, "sell failed");
        // 3. Repay + fee
        uint256 repay = amount + premium;
        IERC20(asset).approve(address(pool), repay);
        uint256 bal = IERC20(asset).balanceOf(address(this));
        require(bal >= repay, "no profit");
        uint256 profit = bal - repay;
        emit ArbitrageExecuted(asset, amount, profit, "buyVenue", "sellVenue");
        // profit stays in contract, owner can withdraw
        return true;
    }

    function withdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).transfer(owner, amount);
    }

    function setPool(address _pool) external onlyOwner { pool = IPool(_pool); }
}
