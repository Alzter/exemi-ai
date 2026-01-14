DROP TABLE Participants;

CREATE TABLE Participants(
    ID INT AUTO INCREMENT NOT NULL PRIMARY KEY,
    PasswordHash VARCHAR(255),
    Disabled BOOL
);

DROP TABLE Conversations

CREATE TABLE Conversations(
    ID INT AUTO INCREMENT NOT NULL PRIMARY KEY,
    CreatedAt DATETIME
)

DROP TABLE MESSAGES

CREATE TABLE Messages (
    ID INT PRIMARY KEY,
    ConversationID INT,
    Role VARCHAR(255),
    Content VARCHAR(255),
    CreatedAt DATEIMTE,
)

# Create FK Constraint between message IDs and conversation IDs
