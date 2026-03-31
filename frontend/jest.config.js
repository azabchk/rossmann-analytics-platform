const config = {
  testEnvironment: "jsdom",
  moduleFileExtensions: ["js", "ts", "tsx"],
  testMatch: ["<rootDir>/tests/**/*.test.ts?(x)"],
  roots: ["<rootDir>/tests"],
  setupFilesAfterEnv: ["<rootDir>/tests/jest.setup.ts"],
  transform: {
    "^.+\\.(ts|tsx)$": [
      "ts-jest",
      {
        tsconfig: "<rootDir>/tsconfig.jest.json",
      },
    ],
  },
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
};

module.exports = config;
